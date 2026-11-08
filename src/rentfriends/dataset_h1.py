"""Dataset preparation for the H1 hypothesis in RentFriends.

Implements decisions:
- D6: Main analysis does not exclude extreme or low-activity accounts (sensitivity flags provided).
- D7: Profile features taken as of the swipe day (prior_version, first_version, users_current).
- D8: Gender 'O' is treated as a separate distinct category.
- D9: Age bands 27+ merged into '27+' (18-20, 21-23, 24-26, 27+).
- D10: Accounts with city 'Hyderabad' are dropped from main analysis.
- D12: Separation of tags: lifestyle, hobby (interests), and status ('student').
- D13: Structured fields have priority; linked lifestyle tags fill missing values (no redundancy).
- D14, D15: Lifestyle block: structured agreement, shared non-linked tags, directional conflicts.
- D16: Interests block: Jaccard similarity of pure interests, shared count, count difference.
- D17: Direct modeling of outcomes without close-to-zero threshold or two-stage gating.
- Excludes all bio fields (bio effort is reserved for H3).
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Core constants
AGE_BAND_MERGE: dict[str, str] = {
    "18-20": "18-20",
    "21-23": "21-23",
    "24-26": "24-26",
    "27-30": "27+",
    "31-35": "27+",
    "36+": "27+",
}

AGE_BAND_ORDER: dict[str, int] = {
    "18-20": 0,
    "21-23": 1,
    "24-26": 2,
    "27+": 3,
}

RAW_TAG_CAP = 9  # maximum number of interest tags a profile can hold in the app

LIFESTYLE_STRUCTURED_FIELDS: list[str] = [
    "daily_routine",
    "lifestyle",
    "work_from_home",
    "cleanliness",
    "noise_level",
    "smoking",
    "alcohol",
]

# Mapping from canonical lifestyle tags to (field_name, imputed_code) per D13
TAG_TO_STRUCTURED_FIELD_MAP: dict[str, tuple[str, str]] = {
    "smoker": ("smoking", "Y"),
    "non_smoker": ("smoking", "N"),
    "early_bird": ("daily_routine", "EB"),
    "night_owl": ("daily_routine", "NO"),
    "loves_cleanliness": ("cleanliness", "VT"),
    "works_remote": ("work_from_home", "Y"),
    "quiet_evenings": ("noise_level", "Q"),
    "silence_after_22": ("noise_level", "Q"),
    "likes_calm": ("noise_level", "Q"),
    "peace_and_quite": ("noise_level", "Q"),
    "likes_parties": ("noise_level", "P"),
    "music_nonstop": ("noise_level", "P"),
}

# Directional polarity groups for lifestyle tag conflicts (D15)
POLARITY_PAIRS: list[tuple[set[str], set[str]]] = [
    ({"smoker"}, {"non_smoker"}),
    ({"early_bird"}, {"night_owl"}),
    ({"extrovert"}, {"introvert"}),
    ({"no_pets"}, {"animals", "cat_person", "dog_person"}),
    (
        {"likes_calm", "quiet_evenings", "silence_after_22", "chill_at_home", "mostly_home"},
        {"likes_parties", "music_nonstop"},
    ),
]


def load_tag_mappings(
    mapping_csv_path: str | Path,
    proposal_csv_path: str | Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Load tag-to-canonical mapping and canonical-to-category / linked_field mappings."""
    mapping_df = pd.read_csv(mapping_csv_path)
    mapping_dict = dict(zip(mapping_df.iloc[:, 0], mapping_df.iloc[:, 1], strict=False))

    tag_prop_df = pd.read_csv(proposal_csv_path)
    category_dict = dict(
        zip(
            tag_prop_df["canonical_tag"],
            tag_prop_df["proposed_category_claude"],
            strict=False,
        )
    )
    linked_field_dict = dict(
        zip(
            tag_prop_df["canonical_tag"],
            tag_prop_df["proposed_linked_field"],
            strict=False,
        )
    )

    for cat in ["hobby", "lifestyle", "status", "unclear"]:
        category_dict[f"other_{cat}"] = cat
        linked_field_dict[f"other_{cat}"] = "none"

    return mapping_dict, category_dict, linked_field_dict


def parse_raw_interests(raw: Any) -> list[str]:
    """Parse raw interests column into a list of strings."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    if isinstance(raw, list | tuple):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            val = ast.literal_eval(raw)
            if isinstance(val, list | tuple):
                return [str(x) for x in val]
        except Exception:
            try:
                val = json.loads(raw)
                if isinstance(val, list | tuple):
                    return [str(x) for x in val]
            except Exception:
                return []
    return []


def get_infrequent_canonical_tags(
    interests_series: pd.Series,
    mapping_dict: dict[str, str],
    min_samples: int = 50,
) -> set[str]:
    """Identify canonical tags with fewer than min_samples occurrences."""
    canonical_tags: list[str] = []
    for item in interests_series:
        for tag in parse_raw_interests(item):
            canonical_tags.append(mapping_dict.get(tag, tag))
    counts = pd.Series(canonical_tags).value_counts()
    return set(counts[counts < min_samples].index)


def transform_and_disentangle_tags(
    raw_interests: Any,
    mapping_dict: dict[str, str],
    category_dict: dict[str, str],
    infrequent_tags: set[str],
) -> tuple[list[str], list[str], list[str]]:
    """Transform tags and separate pure interests from lifestyle and status tags (D12, D13).

    Returns:
        pure_interests: hobby/interest tags (strictly free of lifestyle/status duplication)
        lifestyle_tags: lifestyle habit tags (used for lifestyle matching / D13 imputation)
        status_tags: occupational / social status tags ('student')
    """
    tags = parse_raw_interests(raw_interests)
    transformed: list[str] = []
    for tag in tags:
        canonical = mapping_dict.get(tag, tag)
        if canonical in infrequent_tags:
            cat = category_dict.get(canonical, "unclear")
            canonical = f"other_{cat}"
        transformed.append(canonical)

    deduped = list(dict.fromkeys(transformed))

    pure_interests: list[str] = []
    lifestyle_tags: list[str] = []
    status_tags: list[str] = []

    for t in deduped:
        cat = category_dict.get(t, "unclear")
        if cat == "hobby":
            pure_interests.append(t)
        elif cat == "lifestyle":
            lifestyle_tags.append(t)
        elif cat == "status":
            status_tags.append(t)
        else:
            # Unclear tags are kept in interests only if not lifestyle
            pure_interests.append(t)

    return pure_interests, lifestyle_tags, status_tags


def apply_d13_tag_imputation(
    df: pd.DataFrame,
    lifestyle_tags_col: str = "lifestyle_tags",
) -> pd.DataFrame:
    """Implement D13: structured field has priority; linked lifestyle tag fills missing value."""
    res = df.copy()
    for tag, (field, code) in TAG_TO_STRUCTURED_FIELD_MAP.items():
        if field in res.columns:
            has_tag = res[lifestyle_tags_col].apply(lambda tags, t=tag: t in tags)
            mask = res[field].isna() & has_tag
            res.loc[mask, field] = code
    return res


def resolve_as_of_profiles(
    query_df: pd.DataFrame,
    profile_history: pd.DataFrame,
    users: pd.DataFrame,
    user_col: str,
    day_col: str = "day",
    prefix: str = "",
    profile_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Resolve user profile snapshot as of the swipe day according to D7."""
    if profile_cols is None:
        profile_cols = [
            "sex",
            "age_band",
            "city",
            *LIFESTYLE_STRUCTURED_FIELDS,
            "pure_interests",
            "lifestyle_tags",
        ]

    history_clean = profile_history.copy()
    history_clean["user_key"] = history_clean["user_key"].astype(str)
    history_clean["day"] = history_clean["day"].astype("int64")

    history_daily_latest = (
        history_clean.sort_values(["day", "version"])
        .groupby(["user_key", "day"], as_index=False)
        .last()
        .sort_values("day")
        .reset_index(drop=True)
    )

    v1 = history_clean.sort_values("version").groupby("user_key").first().reset_index()
    v1_map = v1.set_index("user_key")
    users_clean = users.copy()
    users_clean["user_key"] = users_clean["user_key"].astype(str)
    users_map = users_clean.set_index("user_key")

    v1_day = history_clean.groupby("user_key")["day"].min()
    users_with_hist = set(v1_day.index)

    sub = query_df[[user_col, day_col]].copy()
    sub[user_col] = sub[user_col].astype(str)
    sub[day_col] = sub[day_col].astype("int64")
    sub["_orig_order"] = np.arange(len(sub))
    sub = sub.sort_values(day_col).reset_index(drop=True)

    available_cols = [c for c in profile_cols if c in history_daily_latest.columns]
    merged = pd.merge_asof(
        sub,
        history_daily_latest[["user_key", "day", *available_cols]],
        left_on=day_col,
        right_on="day",
        left_by=user_col,
        right_by="user_key",
        direction="backward",
        allow_exact_matches=False,
        suffixes=("", "_hist"),
    )

    u_series = merged[user_col]
    d_series = merged[day_col]

    is_in_hist = u_series.isin(users_with_hist)
    u_v1_day = u_series.map(v1_day)

    flag = pd.Series("prior_version", index=merged.index)
    flag[~is_in_hist] = "users_current"
    flag[is_in_hist & (d_series <= u_v1_day)] = "first_version"
    merged["source_flag"] = flag

    mask_v1 = merged["source_flag"] == "first_version"
    if mask_v1.any():
        for col in available_cols:
            if col in v1_map.columns:
                merged.loc[mask_v1, col] = u_series[mask_v1].map(v1_map[col])

    mask_curr = merged["source_flag"] == "users_current"
    if mask_curr.any():
        for col in available_cols:
            if col in users_map.columns:
                merged.loc[mask_curr, col] = u_series[mask_curr].map(users_map[col])

    merged = merged.sort_values("_orig_order").reset_index(drop=True)

    out = pd.DataFrame(index=merged.index)
    out[f"{prefix}source_flag"] = merged["source_flag"]
    for col in available_cols:
        out[f"{prefix}{col}"] = merged[col]

    return out


def idf_weights(tag_sets: Iterable[Iterable[str]], n_docs: int | None = None) -> dict[str, float]:
    """Inverse document frequency log(N / df) of every tag; a tag in all documents weighs 0."""
    docs = [set(t) for t in tag_sets]
    n = len(docs) if n_docs is None else n_docs
    counts: dict[str, int] = {}
    for doc in docs:
        for tag in doc:
            counts[tag] = counts.get(tag, 0) + 1
    return {tag: float(np.log(n / df)) for tag, df in counts.items()}


def weighted_jaccard(
    a: set[str] | Iterable[str],
    b: set[str] | Iterable[str],
    weights: dict[str, float],
    default_weight: float = 0.0,
) -> float:
    """IDF-weighted Jaccard: weight of shared tags over weight of all tags (0 if empty)."""
    sa, sb = set(a), set(b)
    union_w = sum(weights.get(t, default_weight) for t in sa | sb)
    if union_w <= 0:
        return 0.0
    inter_w = sum(weights.get(t, default_weight) for t in sa & sb)
    return float(inter_w / union_w)


def field_agreement_status(sender: pd.Series, receiver: pd.Series) -> pd.Series:
    """Per-field pair status: agree / disagree / one_missing / both_missing (Z7)."""
    s_na, r_na = sender.isna().to_numpy(), receiver.isna().to_numpy()
    out = np.where(
        s_na & r_na,
        "both_missing",
        np.where(
            s_na | r_na,
            "one_missing",
            np.where(sender.to_numpy() == receiver.to_numpy(), "agree", "disagree"),
        ),
    )
    return pd.Series(out, index=sender.index)


def smoking_direction(sender: pd.Series, receiver: pd.Series) -> pd.Series:
    """Directional smoking status. Code `N` is read as non-smoker, any other code as a user.

    There is no codebook for the field (D14), so this reading of `V`, `O`, `Y` is an assumption.
    """
    status = field_agreement_status(sender, receiver)
    s_n, r_n = (sender == "N").to_numpy(), (receiver == "N").to_numpy()
    out = status.to_numpy().astype(object)
    both = status.isin(["agree", "disagree"]).to_numpy()
    out[both & s_n & ~r_n] = "nonsmoker_to_user"
    out[both & ~s_n & r_n] = "user_to_nonsmoker"
    out[both & ~s_n & ~r_n & (status == "disagree").to_numpy()] = "user_vs_other_user"
    return pd.Series(out, index=sender.index)


def compute_lifestyle_tag_conflict(tags_a: list[str], tags_b: list[str]) -> int:
    """Check if pair has conflicting directional lifestyle preferences (D15)."""
    set_a = set(tags_a)
    set_b = set(tags_b)
    for group_pos, group_neg in POLARITY_PAIRS:
        if (set_a & group_pos and set_b & group_neg) or (set_a & group_neg and set_b & group_pos):
            return 1
    return 0


def build_h1_dataset(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
) -> pd.DataFrame:
    """Build the clean analytical dataset for the H1 hypothesis."""
    data_path = Path(data_dir)
    docs_path = Path(docs_dir)

    # 1. Load data
    swipes = pd.read_parquet(data_path / "swipes.parquet")
    history = pd.read_parquet(data_path / "profile_history.parquet")
    users = pd.read_parquet(data_path / "users.parquet")
    matches = pd.read_parquet(data_path / "matches.parquet")

    mapping_dict, category_dict, _ = load_tag_mappings(
        docs_path / "interests_mapping.csv",
        docs_path / "tag_category_proposal.csv",
    )

    # 2. Exclude accounts with city Hyderabad (D10)
    hyderabad_users = set(users[users["city"] == "Hyderabad"]["user_key"])

    # Filter to profile swipes
    profile_swipes = swipes[swipes["target_type"] == "profile"].copy()
    mask_hyd = profile_swipes["user_key"].isin(hyderabad_users) | profile_swipes[
        "target_user_key"
    ].isin(hyderabad_users)
    df_swipes = profile_swipes[~mask_hyd].copy().reset_index(drop=True)

    # 3. Disentangle interests from lifestyle and apply D13
    infrequent_tags = get_infrequent_canonical_tags(
        users["interests"], mapping_dict, min_samples=50
    )

    for df in [history, users]:
        split_res = df["interests"].apply(
            lambda raw: transform_and_disentangle_tags(
                raw, mapping_dict, category_dict, infrequent_tags
            )
        )
        df["pure_interests"] = [s[0] for s in split_res]
        df["lifestyle_tags"] = [s[1] for s in split_res]
        df["raw_tags_n"] = df["interests"].apply(lambda raw: len(parse_raw_interests(raw)))
        # Apply D13: structured field priority, tag fills missing values
        df_imputed = apply_d13_tag_imputation(df, lifestyle_tags_col="lifestyle_tags")
        for field in LIFESTYLE_STRUCTURED_FIELDS:
            df[field] = df_imputed[field]

    # 4. Resolve as-of profiles for sender and receiver (D7)
    cols_to_resolve = [
        "sex",
        "age_band",
        "city",
        *LIFESTYLE_STRUCTURED_FIELDS,
        "pure_interests",
        "lifestyle_tags",
        "raw_tags_n",
    ]

    # IDF over the current profiles of non-excluded users (Z6a)
    idf_docs = users.loc[~users["user_key"].isin(hyderabad_users), "pure_interests"]
    tag_weights = idf_weights(idf_docs, n_docs=len(idf_docs))
    unseen_weight = float(np.log(max(len(idf_docs), 1)))  # rarest possible tag

    sender_prof = resolve_as_of_profiles(
        df_swipes,
        history,
        users,
        user_col="user_key",
        day_col="day",
        prefix="sender_",
        profile_cols=cols_to_resolve,
    )
    receiver_prof = resolve_as_of_profiles(
        df_swipes,
        history,
        users,
        user_col="target_user_key",
        day_col="day",
        prefix="receiver_",
        profile_cols=cols_to_resolve,
    )

    # 5. Build match lookup
    match_pairs = set()
    for _, r in matches.iterrows():
        match_pairs.add((str(r["user_a_key"]), str(r["user_b_key"])))
        match_pairs.add((str(r["user_b_key"]), str(r["user_a_key"])))

    # 6. Assemble dataset columns
    res = pd.DataFrame(index=df_swipes.index)
    res["user_key"] = df_swipes["user_key"].astype(str)
    res["target_user_key"] = df_swipes["target_user_key"].astype(str)
    res["day"] = df_swipes["day"].astype(int)

    # Outcomes (D4, D5, D17)
    res["y_right"] = (df_swipes["direction"] == "right").astype(int)
    pair_tuples = list(zip(res["user_key"], res["target_user_key"], strict=False))
    res["match"] = [int(p in match_pairs) for p in pair_tuples]

    # Temporal source flags (D7)
    res["source_flag_receiver"] = receiver_prof["receiver_source_flag"]
    res["source_flag_sender"] = sender_prof["sender_source_flag"]
    res["both_prior_version"] = (
        (res["source_flag_receiver"] == "prior_version")
        & (res["source_flag_sender"] == "prior_version")
    ).astype(int)

    # Demographics: Sex (D8)
    res["sex_sender"] = sender_prof["sender_sex"]
    res["sex_receiver"] = receiver_prof["receiver_sex"]
    res["same_sex"] = (res["sex_sender"] == res["sex_receiver"]).astype(int)
    res["sex_pair"] = res["sex_sender"].astype(str) + "_" + res["sex_receiver"].astype(str)

    # Demographics: Age band with 27+ merged (D9)
    res["age_band_sender"] = sender_prof["sender_age_band"].map(AGE_BAND_MERGE)
    res["age_band_receiver"] = receiver_prof["receiver_age_band"].map(AGE_BAND_MERGE)
    res["same_band"] = (res["age_band_sender"] == res["age_band_receiver"]).astype(int)

    idx_sender = res["age_band_sender"].map(AGE_BAND_ORDER)
    idx_receiver = res["age_band_receiver"].map(AGE_BAND_ORDER)
    res["age_band_diff"] = idx_receiver - idx_sender
    res["age_band_diff_abs"] = res["age_band_diff"].abs()

    # City control
    res["city_sender"] = sender_prof["sender_city"]
    res["city_receiver"] = receiver_prof["receiver_city"]
    both_known_city = (
        res["city_sender"].notna()
        & res["city_receiver"].notna()
        & (res["city_sender"] != "inne")
        & (res["city_receiver"] != "inne")
    )
    res["same_city"] = np.where(
        ~both_known_city,
        "unknown",
        np.where(res["city_sender"] == res["city_receiver"], "same", "different"),
    )

    # Lifestyle block (D13, D14, D15)
    agreed_fields = np.zeros(len(res), dtype=int)
    known_fields = np.zeros(len(res), dtype=int)

    for field in LIFESTYLE_STRUCTURED_FIELDS:
        s_val = sender_prof[f"sender_{field}"]
        r_val = receiver_prof[f"receiver_{field}"]
        known_mask = s_val.notna() & r_val.notna()
        agree_mask = known_mask & (s_val == r_val)
        agreed_fields += agree_mask.astype(int)
        known_fields += known_mask.astype(int)

    res["lifestyle_agreed_count"] = agreed_fields
    res["lifestyle_known_count"] = known_fields
    res["lifestyle_agree_ratio"] = np.where(
        known_fields > 0, agreed_fields / np.maximum(known_fields, 1), np.nan
    )

    s_ltags = sender_prof["sender_lifestyle_tags"]
    r_ltags = receiver_prof["receiver_lifestyle_tags"]
    res["lifestyle_shared_tags_n"] = [
        len(set(s) & set(r)) for s, r in zip(s_ltags, r_ltags, strict=False)
    ]
    res["lifestyle_tag_conflict"] = [
        compute_lifestyle_tag_conflict(s, r) for s, r in zip(s_ltags, r_ltags, strict=False)
    ]

    # Interests block (D12, D16) - pure interests strictly separated from lifestyle
    s_pure = sender_prof["sender_pure_interests"]
    r_pure = receiver_prof["receiver_pure_interests"]

    interests_jaccards: list[float] = []
    interests_shared_counts: list[int] = []
    interests_count_diffs: list[int] = []

    for s, r in zip(s_pure, r_pure, strict=False):
        set_s, set_r = set(s), set(r)
        union = set_s | set_r
        inter = set_s & set_r
        jaccard = (len(inter) / len(union)) if union else 0.0
        interests_jaccards.append(jaccard)
        interests_shared_counts.append(len(inter))
        interests_count_diffs.append(len(set_r) - len(set_s))

    res["interests_jaccard"] = interests_jaccards
    res["interests_shared_n"] = interests_shared_counts
    res["interests_count_sender"] = [len(s) for s in s_pure]
    res["interests_count_receiver"] = [len(r) for r in r_pure]
    res["interests_count_diff"] = interests_count_diffs
    res["interests_count_diff_abs"] = np.abs(interests_count_diffs)

    # Z6a: IDF-weighted Jaccard (rare shared tags count more)
    res["interests_idf_jaccard"] = [
        weighted_jaccard(s, r, tag_weights, default_weight=unseen_weight)
        for s, r in zip(s_pure, r_pure, strict=False)
    ]
    # Z6c: raw tag count hits the app's cap of 9 tags before de-duplication / category split
    res["raw_tags_n_sender"] = sender_prof["sender_raw_tags_n"].astype(float)
    res["raw_tags_n_receiver"] = receiver_prof["receiver_raw_tags_n"].astype(float)
    res["interests_at_cap"] = (
        (res["raw_tags_n_sender"] >= RAW_TAG_CAP) | (res["raw_tags_n_receiver"] >= RAW_TAG_CAP)
    ).astype(int)
    # Z6b: canonical hobby tag sets per swipe side (aggregate-level categories, never bio text)
    res["interests_set_sender"] = [sorted(set(x)) for x in s_pure]
    res["interests_set_receiver"] = [sorted(set(x)) for x in r_pure]

    # Z7: per-field pair status and smoking direction
    for field in LIFESTYLE_STRUCTURED_FIELDS:
        res[f"lsf_{field}"] = field_agreement_status(
            sender_prof[f"sender_{field}"], receiver_prof[f"receiver_{field}"]
        )
    res["smoking_direction"] = smoking_direction(
        sender_prof["sender_smoking"], receiver_prof["receiver_smoking"]
    )

    # Sensitivity analysis flags (D6)
    user_swipe_counts = res.groupby("user_key")["y_right"].agg(["count", "mean"])
    res["sender_total_swipes"] = res["user_key"].map(user_swipe_counts["count"])
    res["sender_right_rate"] = res["user_key"].map(user_swipe_counts["mean"])

    res["is_low_activity"] = (res["sender_total_swipes"] < 10).astype(int)
    res["is_extreme_user"] = (
        (res["sender_right_rate"] == 0.0) | (res["sender_right_rate"] == 1.0)
    ).astype(int)

    return res
