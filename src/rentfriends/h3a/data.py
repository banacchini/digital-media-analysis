"""Loading, as-of profile assignment (D7) and the swipe-level H3a analysis table.

The analysis table lives only in memory. User keys are replaced by integer codes before
modelling; nothing row-level is written to disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from rentfriends.h3a import variables as v
from rentfriends.h3a.config import (
    AGE_BAND_LABEL,
    DATA_DIR,
    HYDERABAD,
    LIFESTYLE_FIELDS,
    MAPPING_CSV,
)

PROFILE_COLS = [
    "sex",
    "age_band",
    "city",
    *LIFESTYLE_FIELDS,
    "interests",
    "bio",
    "bio_length",
]


@dataclass
class RawData:
    users: pd.DataFrame
    history: pd.DataFrame
    swipes: pd.DataFrame
    mapping: pd.DataFrame


def load_raw(data_dir: Path = DATA_DIR, mapping_csv: Path = MAPPING_CSV) -> RawData:
    """Read the three tables needed for H3a plus the tag mapping."""
    return RawData(
        users=pd.read_parquet(data_dir / "users.parquet"),
        history=pd.read_parquet(data_dir / "profile_history.parquet"),
        swipes=pd.read_parquet(data_dir / "swipes.parquet"),
        mapping=pd.read_csv(mapping_csv),
    )


def assign_asof(
    events: pd.DataFrame,
    history: pd.DataFrame,
    user_col: str,
    users_without_history: set | None = None,
) -> pd.DataFrame:
    """Assign a profile version to each event by the D7 as-of rule.

    1. event day later than the user's first version day -> last version with day < event day
       (`prior_version`; among same-day versions the highest version number is used);
    2. event on or before the first version day -> the oldest version (`first_version`);
    3. user without any history -> current `users` row (`users_current`, version = -1).

    Returns a frame aligned with `events.index` with columns `version` and `asof_source`.
    """
    users_without_history = users_without_history or set()
    ev = events[[user_col, "day"]].copy()
    ev["_row"] = np.arange(len(ev))
    h = (
        history[["user_key", "version", "day"]]
        .sort_values(["user_key", "day", "version"])
        .drop_duplicates(["user_key", "day"], keep="last")
        .rename(columns={"user_key": user_col, "day": "vday"})
    )
    first = history.sort_values("version").groupby("user_key")["version"].first()

    ev_sorted = ev.sort_values("day")
    h_sorted = h.sort_values("vday")
    merged = pd.merge_asof(
        ev_sorted,
        h_sorted,
        left_on="day",
        right_on="vday",
        by=user_col,
        allow_exact_matches=False,
        direction="backward",
    ).sort_values("_row")

    version = merged["version"].to_numpy(dtype=float, copy=True)
    source = np.where(np.isnan(version), "first_version", "prior_version").astype(object)
    users_arr = merged[user_col].to_numpy()
    first_v = pd.Series(users_arr).map(first).to_numpy(dtype=float, copy=True)
    no_prior = np.isnan(version)
    version[no_prior] = first_v[no_prior]
    no_hist = np.isnan(version)
    if no_hist.any():
        unknown = set(users_arr[no_hist]) - set(users_without_history)
        if unknown:
            raise ValueError(f"{len(unknown)} users have neither history nor a users row")
        version[no_hist] = -1
        source[no_hist] = "users_current"
    return pd.DataFrame({"version": version.astype(int), "asof_source": source}, index=events.index)


def profile_features(snap: pd.DataFrame, tag_map: dict[str, str]) -> pd.DataFrame:
    """All per-snapshot features used for either side of the pair."""
    out = pd.concat(
        [
            v.bio_features(snap["bio"], snap["bio_length"]),
            v.tag_counts(snap["interests"], tag_map),
            v.completeness_features(snap),
        ],
        axis=1,
    )
    out["sex"] = snap["sex"].astype("string")
    out["age_idx"] = v.age_index(snap["age_band"])
    out["city"] = snap["city"].astype("string")
    for f in LIFESTYLE_FIELDS:
        out[f"ls_{f}"] = snap[f].astype("string").fillna("brak").replace("", "brak")
    return out


def snapshot_table(raw: RawData) -> pd.DataFrame:
    """Features for every (user_key, version); version = -1 is the current users row."""
    tag_map = v.build_tag_map(raw.mapping)
    hist = raw.history[["user_key", "version", *PROFILE_COLS]].copy()
    cur = raw.users[["user_key", *PROFILE_COLS]].copy()
    cur["version"] = -1
    snaps = pd.concat([hist, cur], ignore_index=True)
    feats = profile_features(snaps, tag_map)
    feats.insert(0, "user_key", snaps["user_key"].to_numpy())
    feats.insert(1, "version", snaps["version"].to_numpy())
    return feats


@dataclass
class AnalysisData:
    table: pd.DataFrame  # swipe-level, in memory only
    flow: list[dict] = field(default_factory=list)
    checks: dict = field(default_factory=dict)


def hyderabad_users(raw: RawData) -> set:
    """Accounts whose current `users.city` is Hyderabad (D10)."""
    return set(raw.users.loc[raw.users["city"] == HYDERABAD, "user_key"])


def build_analysis_table(raw: RawData, use_current_users: bool = False) -> AnalysisData:
    """Swipe-level table with as-of features of sender (`s_`) and receiver (`r_`).

    `use_current_users=True` builds S2b: every swipe gets the current `users` row.
    Hyderabad accounts are flagged, not dropped (the filter is applied in `analysis_sample`).
    """
    sw = raw.swipes
    prof = sw.loc[
        sw["target_type"] == "profile", ["user_key", "target_user_key", "direction", "day"]
    ]
    prof = prof.reset_index(drop=True)
    no_hist = set(raw.users["user_key"]) - set(raw.history["user_key"])
    snaps = snapshot_table(raw).set_index(["user_key", "version"])

    out = pd.DataFrame({"day": prof["day"].to_numpy()})
    out["y_right"] = (prof["direction"] == "right").astype(int).to_numpy()
    for side, col in (("s", "user_key"), ("r", "target_user_key")):
        if use_current_users:
            asof = pd.DataFrame({"version": -1, "asof_source": "users_current"}, index=prof.index)
        else:
            asof = assign_asof(prof, raw.history, col, no_hist)
        keys = pd.MultiIndex.from_arrays([prof[col].to_numpy(), asof["version"].to_numpy()])
        f = snaps.reindex(keys).reset_index(drop=True)
        f.columns = [f"{side}_{c}" for c in f.columns]
        out = pd.concat([out, f], axis=1)
        out[f"{side}_asof_source"] = asof["asof_source"].to_numpy()
        out[f"{side}_version"] = asof["version"].to_numpy()
        out[f"{side}_key"] = prof[col].to_numpy()

    hyd = hyderabad_users(raw)
    out["hyderabad"] = (out["s_key"].isin(hyd) | out["r_key"].isin(hyd)).astype(int)
    out = add_pair_features(out)
    return AnalysisData(table=out)


def add_pair_features(t: pd.DataFrame) -> pd.DataFrame:
    """Pair-level model variables (codebook part C names)."""
    t["sex_pair"] = v.sex_pair(t["s_sex"], t["r_sex"])
    t["sender_sex"] = t["s_sex"]
    t["age_band_diff"] = t["r_age_idx"] - t["s_age_idx"]
    t["same_band"] = (t["r_age_idx"] == t["s_age_idx"]).astype(float)
    t.loc[t["age_band_diff"].isna(), "same_band"] = np.nan
    t["same_city"] = v.same_city(t["s_city"], t["r_city"])
    t["receiver_age_band"] = t["r_age_idx"].map(AGE_BAND_LABEL)
    for c in [
        "has_bio",
        "bio_empty",
        "bio_empty_alt10",
        "bio_len",
        "bio_len_cap",
        "profile_completeness",
        "profile_completeness_alt",
        "tag_count_receiver",
        "tag_count_raw",
        "tag_zero",
        "tag_cap",
    ]:
        t[c] = t[f"r_{c}"]
    t["has_bio_alt10"] = 1 - t["bio_empty_alt10"]
    # S6 flags on the raw count.
    t["tag_zero_raw"] = (t["tag_count_raw"] == 0).astype(int)
    t["tag_cap_raw"] = (t["tag_count_raw"] >= 9).astype(int)
    t["asof_source"] = np.where(
        (t["s_asof_source"] == "prior_version") & (t["r_asof_source"] == "prior_version"),
        "prior_version",
        np.where(
            (t["s_asof_source"] == "users_current") | (t["r_asof_source"] == "users_current"),
            "users_current",
            "first_version",
        ),
    )
    t["week"] = t["day"] // 7
    return t


MODEL_VARS = [
    "y_right",
    "has_bio",
    "sex_pair",
    "age_band_diff",
    "same_band",
    "same_city",
    "profile_completeness",
    "tag_count_receiver",
]


def complete_case(t: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """Drop rows with any missing model variable."""
    cols = cols or MODEL_VARS
    return t.dropna(subset=cols)


def sample_by_sender(t: pd.DataFrame, frac: float, seed: int) -> pd.DataFrame:
    """Keep all swipes of a random `frac` of senders (smoke runs)."""
    if frac >= 1.0:
        return t
    senders = np.sort(t["s_key"].unique())
    rng = np.random.default_rng(seed)
    keep = rng.choice(senders, size=max(1, int(round(frac * len(senders)))), replace=False)
    return t[t["s_key"].isin(set(keep))]
