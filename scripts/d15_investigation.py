"""Z1 (rebase v1): prevalence of the D15 tag conflict in v0 and the v1 candidate (scenario vi).

Writes aggregates only (`reports/h1/d15_prevalence.json`); no user keys, no bios.
Run: uv run --frozen python scripts/d15_investigation.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rentfriends import dataset_h1 as d1
from rentfriends import h1, h1_d15
from rentfriends import h1_tagval as tv

DATA, DOCS, TV = Path("data/processed"), Path("docs"), Path("docs/tag-validation")
OUT = Path("reports/h1/d15_prevalence.json")


def v1_kwargs() -> dict:
    base_map, _, _ = d1.load_tag_mappings(
        DOCS / "interests_mapping.csv", DOCS / "tag_category_proposal.csv"
    )
    sc = next(s for s in tv.SCENARIOS if s.key == "vi")
    kwargs, _ = tv.scenario_inputs(
        sc,
        consensus_a=tv.load_consensus_a(TV / "consensus_A.csv", base_map),
        consensus_b=tv.load_consensus_b(TV / "consensus_B.csv"),
        merge=tv.load_merge_map(TV / "tag_merge_map.csv"),
    )
    return kwargs


def summarise(name: str, variant: dict, pairs) -> dict:
    df, sender, receiver = h1_d15.capture_tag_sets(DATA, DOCS, **variant)
    full = tv.with_city_dummies(df)
    keep = full[h1._spec_required_cols(h1.H1Spec())].notna().all(axis=1).to_numpy()
    pairs = variant.get("polarity_pairs") or pairs
    table = h1_d15.prevalence_table(sender, receiver, pairs, keep)
    base = h1_d15.independence_baseline(sender, receiver, pairs, keep, n_perm=200, seed=42)
    s_has = np.array([bool(x) for x in sender])[keep].mean()
    r_has = np.array([bool(x) for x in receiver])[keep].mean()
    n_groups = h1_d15.group_conflicts(sender, receiver, pairs)[keep].sum(axis=1)
    side_n = np.bincount(n_groups, minlength=6)
    return {
        "name": name,
        "n_h1_sample": int(keep.sum()),
        "n_all_rows": len(df),
        "conflict_rate_all_rows": float(df["lifestyle_tag_conflict"].mean()),
        "conflict_rate_h1_sample": float(df.loc[keep, "lifestyle_tag_conflict"].mean()),
        "share_sender_has_lifestyle_tag": float(s_has),
        "share_receiver_has_lifestyle_tag": float(r_has),
        "n_groups_in_conflict_distribution": {int(i): int(v) for i, v in enumerate(side_n)},
        "by_group": table.to_dict(orient="records"),
        "independence_baseline": {str(k): v for k, v in base.items()},
        "n_polarity_groups": len(pairs),
    }


def main() -> None:
    res = {}
    for name, variant in (("v0", {}), ("v1_candidate_vi", v1_kwargs())):
        res[name] = summarise(name, variant, d1.POLARITY_PAIRS)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, v in res.items():
        print(k, v["n_h1_sample"], round(v["conflict_rate_h1_sample"], 4), v["n_polarity_groups"])
        for row in v["by_group"]:
            b = v["independence_baseline"][str(row["group"])]
            print(
                f"  g{row['group']}: conflict {row['conflict_rate']:.4f} indep {b['perm_mean']:.4f}"
                f" [{b['perm_lo']:.4f},{b['perm_hi']:.4f}]  s_any {row['sender_any_tag']:.3f}"
                f" r_any {row['receiver_any_tag']:.3f}"
            )
        print("  n groups in conflict:", v["n_groups_in_conflict_distribution"])
        print(
            "  has tag s/r:",
            v["share_sender_has_lifestyle_tag"],
            v["share_receiver_has_lifestyle_tag"],
        )


if __name__ == "__main__":
    main()
