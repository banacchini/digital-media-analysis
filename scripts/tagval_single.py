#!/usr/bin/env python3
"""Metryki walidacji tagów przy JEDNYM annotatorze (runda 1 + runda powtórna).

Referencja = ocena jednej osoby (runda 1, zamrożona). Rzetelność referencji szacuje test-retest
(runda 2, po przerwie, w nowej losowej kolejności). To NIE jest konsensus wielu osób.

Przykład (zadanie B):
  python tagval_single.py --round1 B_runda1.xlsx --round2 B_retest.xlsx --key canonical_tag \
    --agent-file tag_category_proposal.csv --agent-key canonical_tag \
    --agent-cols proposed_category_claude proposed_category_gemini \
    --weights tag_usage_canonical.csv --weights-key canonical_tag --out-dir wyniki_B

Wyjście: summary.json, disagreements.csv, confusion_<agent>.csv,
unstable_items.csv, final_template.csv
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tagval_metrics import boot_ci, cohen_kappa, gwet_ac1, read_labels  # noqa: E402


def agree_stats(x, y, cats, boot, seed):
    x, y = np.asarray(x), np.asarray(y)
    k = cohen_kappa(x, y, cats)
    return {
        "n": int(len(x)),
        "agreement": float(np.mean(x == y)),
        "kappa": float(k),
        "gwet_ac1": float(gwet_ac1(np.vstack([x, y]).T, cats)),
        "kappa_ci90": boot_ci(lambda idx: cohen_kappa(x[idx], y[idx], cats), len(x), boot, seed),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round1", required=True)
    ap.add_argument("--round2")
    ap.add_argument("--key", required=True)
    ap.add_argument("--agent-file", required=True)
    ap.add_argument("--agent-key", required=True)
    ap.add_argument("--agent-cols", nargs="+", required=True)
    ap.add_argument("--weights")
    ap.add_argument("--weights-key")
    ap.add_argument("--weights-col", default="n_swipes")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--thr-agree-weighted", type=float, default=0.95)
    ap.add_argument("--thr-kappa", type=float, default=0.70)
    ap.add_argument("--thr-retest-kappa", type=float, default=0.60)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    r1 = read_labels(a.round1, a.key).set_index(a.key)["etykieta"]
    if r1.isna().any():
        print(json.dumps({"validation_errors": {"round1_missing_label": int(r1.isna().sum())}}))
        return 1
    items = sorted(r1.index)
    ag = pd.read_csv(a.agent_file, dtype=str).set_index(a.agent_key).loc[items, a.agent_cols]
    r2 = None
    if a.round2:
        r2 = read_labels(a.round2, a.key).set_index(a.key)["etykieta"]
        if r2.isna().any():
            print(json.dumps({"validation_errors": {"round2_missing_label": int(r2.isna().sum())}}))
            return 1
        r2 = r2[r2.index.isin(items)]
    cats = sorted(
        set(r1.values) | set(ag.values.ravel()) | (set(r2.values) if r2 is not None else set())
    )

    res = {"n_items": len(items), "categories": cats, "reference": "single reviewer, round 1"}
    stable_mask = pd.Series(np.nan, index=items, dtype=object)

    # --- test-retest ---
    retest_k = None
    if r2 is not None:
        common = sorted(r2.index)
        x, y = r1.loc[common].values, r2.loc[common].values
        res["retest"] = agree_stats(x, y, cats, a.boot, a.seed)
        retest_k = res["retest"]["kappa"]
        res["retest"]["reliability_ok"] = bool(retest_k >= a.thr_retest_kappa)
        un = [k for k in common if r1[k] != r2[k]]
        pd.DataFrame({a.key: un, "runda1": r1.loc[un].values, "runda2": r2.loc[un].values}).to_csv(
            out / "unstable_items.csv", index=False
        )
        res["retest"]["n_unstable"] = len(un)
        pd.crosstab(pd.Series(x, name="runda1"), pd.Series(y, name="runda2")).to_csv(
            out / "retest_confusion.csv"
        )
        stable_mask.loc[common] = ["stable" if r1[k] == r2[k] else "unstable" for k in common]

    # --- wagi ---
    w = None
    if a.weights:
        wdf = pd.read_csv(a.weights).set_index(a.weights_key or a.key)[a.weights_col]
        w = wdf.reindex(items).fillna(0).values.astype(float)

    # --- agent vs runda 1 ---
    ref = r1.loc[items].values
    models_differ = None
    if len(a.agent_cols) == 2:
        models_differ = (ag[a.agent_cols[0]] != ag[a.agent_cols[1]]).values
    res["agents"], dis = {}, []
    for col in a.agent_cols:
        p = ag[col].values
        r = agree_stats(p, ref, cats, a.boot, a.seed)
        if w is not None:
            r["agreement_weighted"] = float(np.sum(w * (p == ref)) / np.sum(w))
            r["rule_weighted_agreement_pass"] = bool(
                r["agreement_weighted"] >= a.thr_agree_weighted
            )
        r["rule_kappa_pass"] = bool(r["kappa"] >= a.thr_kappa)
        if retest_k and retest_k > 0:
            r["kappa_relative_to_retest"] = float(r["kappa"] / retest_k)
        if models_differ is not None:
            pe = p == ref
            r["agreement_when_models_agree"] = (
                float(np.mean(pe[~models_differ])) if (~models_differ).any() else None
            )
            r["agreement_when_models_differ"] = (
                float(np.mean(pe[models_differ])) if models_differ.any() else None
            )
        if r2 is not None:
            sm = stable_mask.loc[items].values
            for lab in ["stable", "unstable"]:
                m = sm == lab
                r[f"agreement_on_{lab}_items"] = float(np.mean((p == ref)[m])) if m.any() else None
                r[f"n_{lab}_items"] = int(m.sum())
        res["agents"][col] = r
        pd.crosstab(pd.Series(ref, name="runda1"), pd.Series(p, name=col)).to_csv(
            out / f"confusion_{col}.csv"
        )
        for i in np.where(p != ref)[0]:
            dis.append(
                {
                    a.key: items[i],
                    "agent": col,
                    "agent_label": p[i],
                    "runda1": ref[i],
                    "runda2": (r2[items[i]] if (r2 is not None and items[i] in r2.index) else None),
                    "n_swipes": None if w is None else float(w[i]),
                }
            )
    pd.DataFrame(dis).to_csv(out / "disagreements.csv", index=False)
    res["thresholds"] = {
        "agree_weighted": a.thr_agree_weighted,
        "kappa": a.thr_kappa,
        "retest_kappa": a.thr_retest_kappa,
    }
    res["reference_category_counts"] = pd.Series(ref).value_counts().to_dict()

    # szablon do przeglądu rozbieżności (final = runda 1, edytowana PO zamrożeniu metryk)
    tpl = pd.DataFrame({a.key: items, "runda1": ref})
    for c in a.agent_cols:
        tpl[c] = ag[c].values
    tpl["konsensus"] = ref
    tpl.to_csv(out / "final_template.csv", index=False)

    (out / "summary.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if "retest" in res:
        print(
            "test-retest:",
            {
                k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in res["retest"].items()
                if k != "kappa_ci90"
            },
            "ci90=",
            [round(v, 3) for v in res["retest"]["kappa_ci90"]],
        )
    for col, r in res["agents"].items():
        print(
            col,
            {
                k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in r.items()
                if k != "kappa_ci90"
            },
            "ci90=",
            [round(v, 3) for v in r["kappa_ci90"]],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
