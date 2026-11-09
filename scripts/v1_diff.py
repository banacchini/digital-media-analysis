"""Aggregate differences between data contract v0 and v1 (no user keys, no bio).

Run: uv run --frozen python scripts/v1_diff.py  -> reports/h1/v1_diff_vs_v0.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from rentfriends import h1
from rentfriends import h1_tagval as tv
from rentfriends.h1_v1 import V0_FILE, V1_FILE
from rentfriends.tagval_prep import sha256_file

DATA = Path("data/processed")


def main() -> None:
    v0, v1 = pd.read_parquet(DATA / V0_FILE), pd.read_parquet(DATA / V1_FILE)
    full = tv.with_city_dummies(v0)
    mask = full[h1._spec_required_cols(h1.H1Spec())].notna().all(axis=1)
    cols_changed = [
        c
        for c in v0.columns
        if not c.startswith("interests_set")
        and not ((v0[c] == v1[c]) | (v0[c].isna() & v1[c].isna())).all()
    ]
    cols_changed += [
        c
        for c in ("interests_set_sender", "interests_set_receiver")
        if any(list(a) != list(b) for a, b in zip(v0[c], v1[c], strict=True))
    ]
    out = {
        "sha256": {V0_FILE: sha256_file(DATA / V0_FILE), V1_FILE: sha256_file(DATA / V1_FILE)},
        "n_columns": {"v0": v0.shape[1], "v1": v1.shape[1]},
        "n_rows": {"v0": len(v0), "v1": len(v1), "h1_sample": int(mask.sum())},
        "columns_with_any_change": sorted(cols_changed),
        "share_changed_h1_sample": tv.changed_shares(v0, v1, mask),
        "share_changed_all_rows": tv.changed_shares(v0, v1, pd.Series(True, index=v0.index)),
        "means_h1_sample": {
            c: {"v0": float(v0.loc[mask, c].mean()), "v1": float(v1.loc[mask, c].mean())}
            for c in (
                "interests_jaccard",
                "interests_shared_n",
                "interests_count_sender",
                "lifestyle_shared_tags_n",
                "lifestyle_tag_conflict",
                "interests_idf_jaccard",
            )
        },
    }
    path = Path("reports/h1/v1_diff_vs_v0.json")
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
