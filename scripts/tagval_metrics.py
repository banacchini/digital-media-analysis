#!/usr/bin/env python3
"""Metryki zgodności dla walidacji tagów (zadania A i B).

Wejście:
  --annotators A=plik B=plik C=plik   (XLSX z arkuszem "Adnotacje" lub CSV;
                                       kolumny: <key>, etykieta)
  --key canonical_tag                 (kolumna klucza pozycji)
  --agent-file proposal.csv --agent-key canonical_tag \
      --agent-cols proposed_category_claude proposed_category_gemini
  --weights usage.csv --weights-key canonical_tag --weights-col n_swipes   (opcjonalnie)
  --out-dir wyniki/

Wyjście (out-dir): consensus.csv, disagreements.csv, confusion_<agent>.csv, summary.json
Etykiety tagów nie są danymi osobowymi; skrypt nie przetwarza bio.
"""

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def read_labels(path, key):
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xlsm"}:
        df = pd.read_excel(p, sheet_name="Adnotacje", dtype=str)
    else:
        df = pd.read_csv(p, dtype=str)
    df = df[[key, "etykieta"]].copy()
    df[key] = df[key].str.strip()
    df["etykieta"] = df["etykieta"].str.strip()
    return df


def cohen_kappa(a, b, cats):
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def fleiss_kappa(M, cats):
    """M: (n_items x n_raters) etykiet."""
    n, r = M.shape
    counts = np.array([[np.sum(M[i] == c) for c in cats] for i in range(n)], dtype=float)
    Pi = (np.sum(counts**2, axis=1) - r) / (r * (r - 1))
    Pbar = Pi.mean()
    pj = counts.sum(axis=0) / (n * r)
    Pe = np.sum(pj**2)
    return (Pbar - Pe) / (1 - Pe) if Pe < 1 else np.nan


def gwet_ac1(M, cats):
    n, r = M.shape
    counts = np.array([[np.sum(M[i] == c) for c in cats] for i in range(n)], dtype=float)
    Pa = ((np.sum(counts**2, axis=1) - r) / (r * (r - 1))).mean()
    pi = counts.sum(axis=0) / (n * r)
    q = len(cats)
    Pe = np.sum(pi * (1 - pi)) / (q - 1) if q > 1 else 1.0
    return (Pa - Pe) / (1 - Pe) if Pe < 1 else np.nan


def boot_ci(fn, n, B, seed, level=0.90):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        v = fn(idx)
        if np.isfinite(v):
            vals.append(v)
    lo, hi = np.percentile(vals, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotators", nargs="+", required=True)
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
    ap.add_argument("--ceiling-kappa", type=float, default=0.60)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- annotatorzy ---
    ann = {}
    for spec in a.annotators:
        name, path = spec.split("=", 1)
        ann[name] = read_labels(path, a.key).set_index(a.key)["etykieta"]
    names = list(ann)
    items = sorted(set.intersection(*[set(s.index) for s in ann.values()]))
    errors = {"missing_label": 0, "item_mismatch": 0}
    for s in ann.values():
        errors["missing_label"] += int(s.isna().sum())
        if set(s.index) != set(items):
            errors["item_mismatch"] += 1
    if any(errors.values()):
        print(json.dumps({"validation_errors": errors}, ensure_ascii=False))
        return 1

    L = pd.DataFrame({n_: ann[n_].loc[items] for n_ in names})
    ag = pd.read_csv(a.agent_file, dtype=str).set_index(a.agent_key)
    ag = ag.loc[items, a.agent_cols]
    cats = sorted(set(L.values.ravel()) | set(ag.values.ravel()))
    M = L.values

    res = {"n_items": len(items), "annotators": names, "categories": cats}

    # --- zgodność ludzi ---
    pair = {}
    for x, y in itertools.combinations(names, 2):
        pair[f"{x}-{y}"] = {
            "agreement": float(np.mean(L[x] == L[y])),
            "kappa": float(cohen_kappa(L[x], L[y], cats)),
        }
    res["human_pairs"] = pair
    res["human_all_agree"] = float(np.mean([len(set(r)) == 1 for r in M]))
    res["human_fleiss_kappa"] = float(fleiss_kappa(M, cats))
    res["human_gwet_ac1"] = float(gwet_ac1(M, cats))
    res["human_fleiss_kappa_ci90"] = boot_ci(
        lambda idx: fleiss_kappa(M[idx], cats), len(items), a.boot, a.seed
    )

    # --- konsensus (większość; 3-stronny rozstrzał do wspólnej decyzji) ---
    cons, adj = [], []
    for row in M:
        vals, cnt = np.unique(row, return_counts=True)
        if cnt.max() >= 2 and (cnt == cnt.max()).sum() == 1:
            cons.append(vals[cnt.argmax()])
            adj.append(False)
        else:
            cons.append("DO_ROZSTRZYGNIECIA")
            adj.append(True)
    cdf = L.copy()
    cdf["konsensus"] = cons
    cdf["do_rozstrzygniecia"] = adj
    cdf.index.name = a.key
    cdf.to_csv(out / "consensus.csv")
    res["n_to_adjudicate"] = int(sum(adj))
    if sum(adj):
        print(
            f"UWAGA: {sum(adj)} pozycji wymaga wspólnego rozstrzygnięcia (konsensus.csv); "
            "metryki agentów liczone po rozstrzygnięciu."
        )

    # --- agenci vs konsensus ---
    w = None
    if a.weights:
        wdf = pd.read_csv(a.weights).set_index(a.weights_key or a.key)[a.weights_col]
        w = wdf.reindex(items).fillna(0).values.astype(float)
    ok = ~np.array(adj)
    ref = np.array(cons)
    agent_res, dis_rows = {}, []
    models_differ = None
    if len(a.agent_cols) == 2:
        models_differ = (ag[a.agent_cols[0]] != ag[a.agent_cols[1]]).values
    for col in a.agent_cols:
        p = ag[col].values
        r = {}
        r["agreement"] = float(np.mean(p[ok] == ref[ok]))
        r["kappa"] = float(cohen_kappa(p[ok], ref[ok], cats))
        r["gwet_ac1"] = float(gwet_ac1(np.vstack([p[ok], ref[ok]]).T, cats))
        idx_ok = np.where(ok)[0]
        # default args bind the current loop values (avoids B023)
        r["kappa_ci90"] = boot_ci(
            lambda idx, p=p, idx_ok=idx_ok: cohen_kappa(p[idx_ok][idx], ref[idx_ok][idx], cats),
            len(idx_ok),
            a.boot,
            a.seed,
        )
        if w is not None:
            r["agreement_weighted"] = float(np.sum(w[ok] * (p[ok] == ref[ok])) / np.sum(w[ok]))
            r["rule_weighted_agreement_pass"] = bool(
                r["agreement_weighted"] >= a.thr_agree_weighted
            )
        r["rule_kappa_pass"] = bool(r["kappa"] >= a.thr_kappa)
        if models_differ is not None:
            d = models_differ[ok]
            pe = p[ok] == ref[ok]
            r["agreement_when_models_agree"] = float(np.mean(pe[~d])) if (~d).any() else None
            r["agreement_when_models_differ"] = float(np.mean(pe[d])) if d.any() else None
        agent_res[col] = r
        conf = pd.crosstab(
            pd.Series(ref[ok], name="konsensus"), pd.Series(p[ok], name=col), dropna=False
        )
        conf.to_csv(out / f"confusion_{col}.csv")
        for i in np.where(ok & (p != ref))[0]:
            dis_rows.append(
                {
                    a.key: items[i],
                    "agent": col,
                    "agent_label": p[i],
                    "konsensus": ref[i],
                    "wspolny_odczyt_ludzi": "/".join(M[i]),
                    "n_swipes": None if w is None else float(w[i]),
                }
            )
    res["agents"] = agent_res
    res["thresholds"] = {
        "agree_weighted": a.thr_agree_weighted,
        "kappa": a.thr_kappa,
        "human_ceiling_kappa": a.ceiling_kappa,
    }
    res["human_ceiling_ok"] = bool(res["human_fleiss_kappa"] >= a.ceiling_kappa)
    pd.DataFrame(dis_rows).to_csv(out / "disagreements.csv", index=False)
    # rozkład kategorii
    res["category_counts_consensus"] = pd.Series(ref[ok]).value_counts().to_dict()
    (out / "summary.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: res[k]
                for k in [
                    "n_items",
                    "human_fleiss_kappa",
                    "human_gwet_ac1",
                    "n_to_adjudicate",
                    "human_ceiling_ok",
                ]
            },
            ensure_ascii=False,
        )
    )
    for col, r in agent_res.items():
        print(
            col,
            {
                k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in r.items()
                if k != "kappa_ci90"
            },
            "kappa_ci90=",
            [round(x, 3) for x in r["kappa_ci90"]],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
