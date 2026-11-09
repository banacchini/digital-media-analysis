"""Agent-side preparation for the tag validation (tasks Z1-Z4 of the agent prompt).

Blindness rule: the raw -> canonical mapping and the agent proposals must never reach the
terminal or the logs. Everything printed from this module is a count or a column name.
Row-level outputs go to `data/tagval/` (git-ignored) and contain tags only, never user keys.

Run: `uv run --frozen python -m rentfriends.tagval_prep`
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

import pandas as pd

from rentfriends.dataset_h1 import parse_raw_interests, resolve_as_of_profiles
from rentfriends.h1 import prepare_h1_sample

PROPOSAL_SHA256 = "1e5625c563ff65dac2a90d6ff4509ac19633b51669583c07ae2b4ab0a2f94ab8"
NO_MATCH = "brak"  # agent label for a raw string without a mapping entry
SHEET_SEED = 20261109
EXPECTED = {
    "proposal_canonical": 68,
    "mapping_unique_canonical": 67,
    "mapping_unique_raw": 124,
    "mapping_emoji_raw": 54,
    "h1_sample_swipes": 92_754,
}


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proposal_hash_ok(path: str | Path) -> bool:
    return sha256_file(path) == PROPOSAL_SHA256


def is_emoji_form(tag: str) -> bool:
    """A raw string containing a pictogram (Unicode category So), usually emoji plus text."""
    return any(unicodedata.category(ch) == "So" for ch in tag)


def collect_raw_tags(*interest_columns: Iterable[object]) -> list[str]:
    """Sorted unique raw tag strings over any number of raw `interests` columns."""
    tags: set[str] = set()
    for col in interest_columns:
        for raw in col:
            tags.update(parse_raw_interests(raw))
    return sorted(tags)


def agent_mapping_table(raw_tags: Iterable[str], mapping: dict[str, str]) -> pd.DataFrame:
    """Agent mapping per raw string; `brak` where the mapping has no entry."""
    raws = list(raw_tags)
    return pd.DataFrame(
        {"raw_tag": raws, "canonical_tag": [mapping.get(t, NO_MATCH) for t in raws]}
    )


def as_of_raw_tags(
    sample: pd.DataFrame, history: pd.DataFrame, users: pd.DataFrame
) -> tuple[list[frozenset[str]], list[frozenset[str]]]:
    """As-of raw tag sets of sender and receiver per swipe (the same D7 rules as H1)."""
    out = []
    for user_col in ("user_key", "target_user_key"):
        prof = resolve_as_of_profiles(
            sample,
            history,
            users,
            user_col=user_col,
            day_col="day",
            profile_cols=["interests"],
        )
        out.append([frozenset(parse_raw_interests(r)) for r in prof["interests"]])
    return out[0], out[1]


def tag_usage(
    sender_sets: list[frozenset[str]],
    receiver_sets: list[frozenset[str]],
    sender_users: Iterable[str],
    receiver_users: Iterable[str],
    key_name: str,
    transform: Callable[[str], str] | None = None,
) -> pd.DataFrame:
    """Usage weights: `n_swipes` counts a swipe once when the tag is on the sender's OR the
    receiver's profile; `n_profiles` counts distinct users carrying the tag in any swipe."""
    n_swipes: dict[str, int] = defaultdict(int)
    users_by_tag: dict[str, set[str]] = defaultdict(set)
    for s_set, r_set, s_user, r_user in zip(
        sender_sets, receiver_sets, sender_users, receiver_users, strict=True
    ):
        s_tags = {transform(t) for t in s_set} if transform else set(s_set)
        r_tags = {transform(t) for t in r_set} if transform else set(r_set)
        for tag in s_tags | r_tags:
            n_swipes[tag] += 1
        for tag in s_tags:
            users_by_tag[tag].add(str(s_user))
        for tag in r_tags:
            users_by_tag[tag].add(str(r_user))
    rows = [(t, len(users_by_tag[t]), n) for t, n in n_swipes.items()]
    df = pd.DataFrame(rows, columns=[key_name, "n_profiles", "n_swipes"])
    return df.sort_values(key_name).reset_index(drop=True)


def load_h1_sample(data_dir: Path) -> pd.DataFrame:
    """H1 main sample, read-only: the stored contract file, never rebuilt or rewritten."""
    df = pd.read_parquet(data_dir / "h1_analysis_dataset.parquet")
    df["city_same"] = (df["same_city"] == "same").astype(float)
    df["city_diff"] = (df["same_city"] == "different").astype(float)
    return prepare_h1_sample(df)


def run(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
    out_dir: str | Path = "data/tagval",
) -> dict[str, object]:
    """Z1-Z4. Returns a stats dict of counts only."""
    data_path, docs_path, out_path = Path(data_dir), Path(docs_dir), Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    proposal_csv = docs_path / "tag_category_proposal.csv"
    mapping_csv = docs_path / "interests_mapping.csv"
    contract = data_path / "h1_analysis_dataset.parquet"
    before = {p.name: sha256_file(p) for p in (proposal_csv, mapping_csv, contract)}

    stats: dict[str, object] = {
        "proposal_hash": "zgodny" if proposal_hash_ok(proposal_csv) else "niezgodny"
    }
    if stats["proposal_hash"] != "zgodny":
        return stats  # rule 1: stop

    # Z1 ---------------------------------------------------------------------------------
    proposal = pd.read_csv(proposal_csv)
    mapping_df = pd.read_csv(mapping_csv)
    mapping = dict(zip(mapping_df.iloc[:, 0].astype(str), mapping_df.iloc[:, 1], strict=True))
    canon_prop = set(proposal["canonical_tag"])
    canon_map = set(mapping_df.iloc[:, 1])
    stats["z1"] = {
        "proposal_canonical": len(canon_prop),
        "mapping_rows": len(mapping_df),
        "mapping_unique_canonical": len(canon_map),
        "mapping_unique_raw": mapping_df.iloc[:, 0].nunique(),
        "mapping_emoji_raw": sum(is_emoji_form(t) for t in mapping),
        "canonical_in_mapping_not_in_proposal": len(canon_map - canon_prop),
        "canonical_in_proposal_not_in_mapping": len(canon_prop - canon_map),
    }

    # Z2 ---------------------------------------------------------------------------------
    users = pd.read_parquet(data_path / "users.parquet")
    history = pd.read_parquet(data_path / "profile_history.parquet")
    raw_users = collect_raw_tags(users["interests"])
    raw_all = collect_raw_tags(users["interests"], history["interests"])
    pd.DataFrame({"raw_tag": raw_all}).to_csv(out_path / "items_A.csv", index=False)
    agent = agent_mapping_table(raw_all, mapping)
    stats["z2"] = {
        "raw_unique_users": len(raw_users),
        "raw_unique_history_only": len(set(raw_all) - set(raw_users)),
        "raw_unique_total": len(raw_all),
        "raw_with_mapping_entry": int((agent["canonical_tag"] != NO_MATCH).sum()),
        "raw_without_mapping_entry": int((agent["canonical_tag"] == NO_MATCH).sum()),
        "raw_emoji_form": sum(is_emoji_form(t) for t in raw_all),
        "mapping_keys_not_in_data": len(set(mapping) - set(raw_all)),
        "agent_canonical_outside_proposal": int(
            (~agent["canonical_tag"].isin(canon_prop | {NO_MATCH})).sum()
        ),
    }

    # Z3 (inputs only; sheets are built by scripts/tagval_make_sheets.py) -----------------
    agent.to_csv(out_path / "agent_A.csv", index=False)
    labels = sorted(canon_prop)  # alphabetical: proposal order must not hint at categories
    (out_path / "canonical_labels.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
    stats["z3"] = {"canonical_labels": len(labels)}

    # Z4 ---------------------------------------------------------------------------------
    sample = load_h1_sample(data_path)
    s_sets, r_sets = as_of_raw_tags(sample, history, users)
    s_keys = sample["user_key"].astype(str)
    r_keys = sample["target_user_key"].astype(str)
    raw_usage = tag_usage(s_sets, r_sets, s_keys, r_keys, "raw_tag")
    canon_usage = tag_usage(
        s_sets,
        r_sets,
        s_keys,
        r_keys,
        "canonical_tag",
        transform=lambda t: mapping.get(t, NO_MATCH),
    )
    raw_usage.to_csv(out_path / "tag_usage_raw.csv", index=False)
    canon_usage.to_csv(out_path / "tag_usage_canonical.csv", index=False)
    items_in_usage = set(raw_all) & set(raw_usage["raw_tag"])
    stats["z4"] = {
        "h1_sample_swipes": len(sample),
        "swipes_with_any_tag": sum(1 for s, r in zip(s_sets, r_sets, strict=True) if s | r),
        "raw_rows": len(raw_usage),
        "raw_sum_n_swipes": int(raw_usage["n_swipes"].sum()),
        "raw_max_n_swipes": int(raw_usage["n_swipes"].max()),
        "raw_tags_not_in_items_A": len(set(raw_usage["raw_tag"]) - set(raw_all)),
        "items_A_with_zero_usage": len(set(raw_all) - items_in_usage),
        "canonical_rows": len(canon_usage),
        "canonical_sum_n_swipes": int(canon_usage["n_swipes"].sum()),
        "canonical_max_n_swipes": int(canon_usage["n_swipes"].max()),
        "canonical_brak_n_swipes": int(
            canon_usage.loc[canon_usage["canonical_tag"] == NO_MATCH, "n_swipes"].sum()
        ),
        "proposal_tags_with_zero_usage": len(canon_prop - set(canon_usage["canonical_tag"])),
    }

    after = {p.name: sha256_file(p) for p in (proposal_csv, mapping_csv, contract)}
    stats["frozen_files_unchanged"] = before == after
    return stats


def main() -> int:
    print(json.dumps(run(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
