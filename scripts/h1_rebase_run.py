"""H1 rebase on data contract v1 (Z3, Z4): heavy computations, cached per job.

Run: uv run --frozen python scripts/h1_rebase_run.py [--workers 14] [--stage compute|aggregate|all]

compute    runs every bootstrap / CV / permutation job (seed 42) and caches the results under
           data/interim/h1_rebase/ (outside git). A job is skipped when its cache file exists.
aggregate  turns the cache into aggregate tables in reports/h1/rebase/ (committed; no user keys).

Everything here is post hoc (tag validation).
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from rentfriends import dataset_h1 as d1
from rentfriends import h1, h1_audit, h1_rebase, h1_v1
from rentfriends import h1_tagval as tv

DATA = Path("data/processed")
DOCS = Path("docs")
TAGVAL = DOCS / "tag-validation"
CACHE = Path("data/interim/h1_rebase")
OUT = Path("reports/h1/rebase")
SEED, N_BOOT, N_BOOT_CV, N_PERM, N_FOLDS = 42, 1000, 1000, 500, 5
CLUSTERS = {"sender": "user_key", "receiver": "target_user_key"}
SCENARIOS = {
    "i": "v0",
    "ii": "konsensus A+B",
    "iii": "konsensus A",
    "iv": "konsensus B",
    "vi": "v1",
}
BLOCK_DF = {"age": 3, "interests": 3, "lifestyle": 3}

_STATE: dict[str, object] = {}


# --- data ------------------------------------------------------------------------------------
def variant_kwargs(key: str) -> dict:
    base_map, _, _ = d1.load_tag_mappings(
        DOCS / "interests_mapping.csv", DOCS / "tag_category_proposal.csv"
    )
    sc = next(s for s in tv.SCENARIOS if s.key == key)
    kwargs, _ = tv.scenario_inputs(
        sc,
        consensus_a=tv.load_consensus_a(TAGVAL / "consensus_A.csv", base_map),
        consensus_b=tv.load_consensus_b(TAGVAL / "consensus_B.csv"),
        merge=tv.load_merge_map(TAGVAL / "tag_merge_map.csv"),
    )
    return kwargs


def load_datasets() -> dict[str, pd.DataFrame]:
    v0 = tv.with_city_dummies(pd.read_parquet(DATA / h1_v1.V0_FILE))
    out = {"i": v0, "vi": h1_v1.load_v1()}
    for key in ("ii", "iii", "iv"):
        out[key] = tv.with_city_dummies(tv.build_h1_variant(DATA, DOCS, **variant_kwargs(key)))
    keys = ["user_key", "target_user_key", "day"]
    for k, df in out.items():
        assert df[keys].equals(v0[keys]), f"{k} is not row-aligned with v0"
    return out


def idf_for(key: str) -> tuple[dict[str, float], float]:
    if key == "i":
        return h1_v1.user_idf(DATA, DOCS)
    kw = variant_kwargs(key)
    return h1_v1.user_idf(
        DATA,
        DOCS,
        **{
            k: kw[k]
            for k in ("raw_to_canonical_override", "category_override", "tag_merge")
            if kw.get(k)
        },
    )


# --- jobs ------------------------------------------------------------------------------------
def job_list() -> dict[str, tuple]:
    jobs: dict[str, tuple] = {}
    for key in SCENARIOS:
        for c in CLUSTERS:
            jobs[f"boot-{key}-{c}"] = ("boot", key, c, None)
        jobs[f"cv-{key}"] = ("cv", key)
    for key in ("i", "vi"):
        for name in ("perm", "base", "field", "age", "fit"):
            jobs[f"{name}-{key}"] = (name, key)
        for idx in range(1, 12):
            for c in CLUSTERS:
                jobs[f"sens{idx:02d}-{key}-{c}"] = ("boot", key, c, idx)
    return jobs


def run_job(job_id: str) -> str:
    kind, key, *rest = _STATE["jobs"][job_id]  # type: ignore[index]
    df = _STATE["data"][key]  # type: ignore[index]
    path = CACHE / f"{job_id}.pkl"
    if path.exists():
        return f"{job_id}: cached"
    t0 = time.time()
    with threadpool_limits(1):
        if kind == "boot":
            cluster, idx = rest
            spec, sub = h1.H1Spec(), df
            if idx is not None:
                _, sub, spec, _ = h1.sensitivity_scenarios(df)[idx]
            obs, boot = h1_audit.bootstrap_model_loglik(
                sub, cluster_col=CLUSTERS[cluster], n_boot=N_BOOT, seed=SEED, spec=spec
            )
            res = {"obs": obs, "boot": boot, "n": len(h1.prepare_h1_sample(sub, spec))}
        elif kind == "cv":
            oof = h1_audit.oof_predictions(df, N_FOLDS, SEED)
            res = {
                "paired": h1_audit.paired_cv_differences(oof, n_boot=N_BOOT_CV, seed=SEED),
                "levels": h1_rebase.cv_levels(oof, n_boot=N_BOOT_CV, seed=SEED),
                "folds": h1.grouped_cv_h1(df, n_splits=N_FOLDS, seed=SEED),
            }
        elif kind == "perm":
            obs, null, p = h1.permutation_null_lifestyle(df, n_perm=N_PERM, seed=SEED)
            res = {"obs": obs, "null": null, "p": p}
        elif kind == "base":
            w, unseen = _STATE["idf"][key]  # type: ignore[index]
            res = {
                "plain": h1_audit.interests_permutation_baseline(
                    df, n_perm=N_PERM, seed=SEED, n_boot=N_BOOT
                ),
                "idf": h1_audit.interests_permutation_baseline(
                    df, n_perm=N_PERM, seed=SEED, weights=w, default_weight=unseen, n_boot=N_BOOT
                ),
            }
        elif kind == "field":
            res = h1_audit.per_field_analysis(df)
        elif kind == "age":
            res = h1_audit.age_direction_check(df, n_boot=N_BOOT, seed=SEED)
        elif kind == "fit":
            fit = h1.fit_h1_logit_models(df)
            res = {
                "summary": fit["summary"],
                "odds_ratios": fit["odds_ratios"],
                "increments": h1_audit.block_increments_from_fit(fit),
                "n": fit["data_len"],
                "sex_counts": h1_audit.sex_pair_user_counts(df),
                "sample": _sample_description(df),
                "sens": h1.sensitivity_analysis_h1(df),
            }
        else:
            raise ValueError(kind)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(res))
    return f"{job_id}: {time.time() - t0:.0f}s"


def _sample_description(df: pd.DataFrame) -> dict:
    d = h1.prepare_h1_sample(df)
    miss = {
        f: float(df[f"lsf_{f}"].isin(["one_missing", "both_missing"]).mean())
        for f in d1.LIFESTYLE_STRUCTURED_FIELDS
    }
    return {
        "n": len(d),
        "senders": int(d["user_key"].nunique()),
        "receivers": int(d["target_user_key"].nunique()),
        "right_share": float(d["y_right"].mean()),
        "missing_share_by_field": miss,
    }


def compute(workers: int) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    _STATE["data"] = load_datasets()
    _STATE["jobs"] = job_list()
    _STATE["idf"] = {k: idf_for(k) for k in ("i", "vi")}
    pending = [j for j in _STATE["jobs"] if not (CACHE / f"{j}.pkl").exists()]  # type: ignore[union-attr]
    # longest first: the main bootstraps and CV jobs start before the small sensitivity ones
    pending.sort(key=lambda j: (j.startswith("sens"), j))
    print(f"{len(pending)} jobs to run on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("fork")) as pool:
        futures = [pool.submit(run_job, j) for j in pending]
        for f in as_completed(futures):
            print(f.result(), flush=True)


# --- aggregation -----------------------------------------------------------------------------
def load(job_id: str):
    return pickle.loads((CACHE / f"{job_id}.pkl").read_bytes())


def block_summary(key: str, prefix: str = "boot") -> tuple[pd.DataFrame, dict]:
    """Conservative CI table of the block quantities of one dictionary + the raw draws."""
    per_cluster, draws = {}, {}
    for c in CLUSTERS:
        r = load(f"{prefix}-{key}-{c}")
        obs_q = h1_rebase.quantity_draws(h1_rebase.increment_draws(r["obs"]))
        boot_q = h1_rebase.quantity_draws(h1_rebase.increment_draws(r["boot"]))
        per_cluster[c] = h1_rebase.summarise_quantities(obs_q, boot_q)
        draws[c] = (obs_q, boot_q)
    return h1_rebase.conservative_ci(per_cluster["sender"], per_cluster["receiver"]), draws


def reproduction_check() -> dict:
    """v0 must reproduce docs/h1/audit-fixes-2026-11-08.md (published to 2 decimals)."""
    inc = load("fit-i")["increments"].set_index("block")
    published = {"age": 533.19, "interests": 13.93, "lifestyle": 42.51}
    got = {b: float(inc.loc[b, "dll_mean"]) for b in published}
    ok = {b: round(got[b], 2) == published[b] for b in published}
    out = {
        "n": int(load("fit-i")["n"]),
        "n_published": 92754,
        "dll_mean": got,
        "dll_mean_published_2dp": published,
        "max_abs_deviation": max(abs(got[b] - published[b]) for b in published),
        "agree_after_rounding_to_2dp": all(ok.values()) and load("fit-i")["n"] == 92754,
    }
    (OUT / "reproduction_check_v0.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def sensitivity12(key: str) -> pd.DataFrame:
    rows = []
    scen = h1.sensitivity_scenarios(_STATE_DATA[key])
    for idx, (name, _, _, status) in enumerate(scen):
        prefix = f"boot-{key}" if idx == 0 else f"sens{idx:02d}-{key}"
        per = {}
        for c in CLUSTERS:
            r = load(f"{prefix}-{c}")
            obs_q = h1_rebase.quantity_draws(h1_rebase.increment_draws(r["obs"]))
            boot_q = h1_rebase.quantity_draws(h1_rebase.increment_draws(r["boot"]))
            per[c] = h1_rebase.summarise_quantities(obs_q, boot_q)
            n = r["n"]
        t = h1_rebase.conservative_ci(per["sender"], per["receiver"]).set_index(
            ["quantity", "definition"]
        )
        row = {"scenariusz": name, "status": status, "n_swipe": n}
        for q, tag in (
            ("dll: lifestyle", "S"),
            ("dll: age+interests", "WZ"),
            ("diff: lifestyle - age+interests", "S-WZ"),
        ):
            r = t.loc[(q, "last")]
            row[f"{tag}"], row[f"{tag}_lo"], row[f"{tag}_hi"] = (
                r["estimate"],
                r["ci_low"],
                r["ci_high"],
            )
        row["S-WZ_excludes0"] = bool(
            t.loc[("diff: lifestyle - age+interests", "last")]["excludes_zero"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


_STATE_DATA: dict[str, pd.DataFrame] = {}


def reported_numbers(key: str) -> pd.DataFrame:
    """Every number reported in the H1 summary for one dataset: estimate and 95% CI."""
    rows: list[dict] = []

    def add(section, quantity, est, lo=None, hi=None, note=""):
        rows.append(
            {
                "section": section,
                "quantity": quantity,
                "estimate": est,
                "ci_low": lo,
                "ci_high": hi,
                "note": note,
            }
        )

    fit = load(f"fit-{key}")
    smp = fit["sample"]
    add("E1", "n swipe'ów (próba główna)", smp["n"])
    add("E1", "nadawcy", smp["senders"])
    add("E1", "odbiorcy", smp["receivers"])
    add("E1", "odsetek prawych", smp["right_share"])
    blocks, _ = block_summary(key)
    t = blocks.set_index(["quantity", "definition"])
    for q in ("age", "interests", "lifestyle", "age+interests"):
        for d in ("mean", "first", "last"):
            r = t.loc[(f"dll: {q}", d)]
            add(
                "E2",
                f"ΔLL {q} [{d}]",
                r["estimate"],
                r["ci_low"],
                r["ci_high"],
                f"szerszy: {r['wider_is']}",
            )
    for q in ("age+interests", "age", "interests"):
        for d in ("last", "first", "mean"):
            r = t.loc[(f"diff: lifestyle - {q}", d)]
            add(
                "E3",
                f"ΔΔLL styl życia − {q} [{d}]",
                r["estimate"],
                r["ci_low"],
                r["ci_high"],
                f"szerszy: {r['wider_is']}; wyklucza 0: {bool(r['excludes_zero'])}",
            )
    for d in ("mean", "last"):
        r = t.loc[("ratio: lifestyle / interests", d)]
        add(
            "Z4",
            f"stosunek ΔLL styl życia / zainteresowania [{d}]",
            r["estimate"],
            r["ci_low"],
            r["ci_high"],
        )
    for b in ("age", "interests", "lifestyle"):
        r = t.loc[(f"share: {b}", "mean")]
        add("Z4", f"udział bloku {b} w sumie ΔLL", r["estimate"], r["ci_low"], r["ci_high"])

    cv = load(f"cv-{key}")
    paired = cv["paired"].set_index(["metric", "definition", "contrast"])
    for metric in ("logloss", "auc", "auc_pr"):
        for d in ("last", "first"):
            for c in (
                "lifestyle - age+interests",
                "lifestyle - age",
                "lifestyle - interests",
                "gain: lifestyle",
            ):
                r = paired.loc[(metric, d, c)]
                add(
                    "E4/E5",
                    f"CV {metric} [{d}]: {c}",
                    r["estimate"],
                    r["ci_low"],
                    r["ci_high"],
                    "dodatnia = styl życia lepszy / poprawa",
                )
    lv = cv["levels"].set_index(["model", "metric"])
    for m in ("controls", "age", "interests", "lifestyle", "age_interests", "full"):
        for metric in ("auc", "logloss", "auc_pr"):
            r = lv.loc[(m, metric)]
            add(
                "CV poziomy",
                f"{metric} (OOF, zbiorczo): {m}",
                r["estimate"],
                r["ci_low"],
                r["ci_high"],
            )
    folds = cv["folds"].groupby("block")[["auc", "logloss", "auc_pr"]].mean()
    for m in ("controls", "age_interests", "full"):
        add(
            "CV poziomy",
            f"AUC (średnia z 5 foldów): {m}",
            float(folds.loc[m, "auc"]),
            note="bez CI (fold)",
        )

    perm = load(f"perm-{key}")
    lo, hi = np.quantile(perm["null"], [0.025, 0.975])
    add("tasowanie", "ΔLL stylu życia (obserwowane)", perm["obs"])
    add(
        "tasowanie",
        "ΔLL stylu życia (tasowanie odbiorców, średnia i 95% pasmo)",
        float(perm["null"].mean()),
        float(lo),
        float(hi),
        f"p = {perm['p']:.4f} (min 1/{N_PERM + 1})",
    )

    age = load(f"age-{key}")["pooled"].set_index("term")
    for term in ("younger_by_1", "older_by_1", "older_by_2plus"):
        r = age.loc[term]
        add("E6", f"wiek OR: {term}", r["or"], r["ci_low"], r["ci_high"])
    orr = fit["odds_ratios"].set_index("zmienna")
    for v in (
        "same_band",
        "age_band_diff_abs",
        "age_band_diff",
        "lifestyle_agree_ratio",
        "lifestyle_tag_conflict",
        "lifestyle_shared_tags_n",
        "interests_jaccard",
        "interests_shared_n",
        "interests_count_diff_abs",
    ):
        r = orr.loc[v]
        add(
            "model pełny",
            f"OR {v}",
            r["or"],
            r["ci_low"],
            r["ci_high"],
            "SE dwustronnie klastrowane",
        )

    base = load(f"base-{key}")
    for name in ("plain", "idf"):
        s = base[name]["summary"].set_index("group")
        for g in ("right", "left", "right_minus_left"):
            r = s.loc[g]
            add(
                "E7",
                f"zainteresowania {name}: {g}",
                r["observed"],
                r["obs_ci_low"],
                r["obs_ci_high"],
                f"baseline permutacji {r['perm_mean']:.4f} "
                f"[{r['perm_lo']:.4f}; {r['perm_hi']:.4f}]",
            )

    field = load(f"field-{key}")
    f = field["fields"].set_index("field")
    for fld in f.index:
        add(
            "E8",
            f"pole {fld}: p po Holmie",
            float(f.loc[fld, "p_holm"]),
            note=f"ΔLL ostatni {f.loc[fld, 'dll_last']:.2f}; p Walda {f.loc[fld, 'p_raw']:.3f}",
        )
    sm = field["smoking_direction"].set_index("level")
    for lvl in sm.index:
        r = sm.loc[lvl]
        add("E9", f"palenie OR: {lvl}", r["or"], r["ci_low"], r["ci_high"], f"n={int(r['n'])}")
    add("E9", "palenie: test symetrii (p)", float(field["smoking_asymmetry_p"]))
    for fld, share in smp["missing_share_by_field"].items():
        add("E10", f"brak pola {fld} u którejkolwiek strony", share)
    return pd.DataFrame(rows)


def aggregate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _STATE_DATA.update(load_datasets())
    print("reproduction v0:", reproduction_check())
    tables: dict[str, pd.DataFrame] = {}
    draws: dict[str, dict] = {}
    for key in SCENARIOS:
        tables[key], draws[key] = block_summary(key)
        tables[key].assign(scenario=key).to_csv(OUT / f"blocks_{key}.csv", index=False)

    # Z4: dictionary sensitivity ----------------------------------------------------------
    rows = []
    for key, label in SCENARIOS.items():
        t = tables[key].set_index(["quantity", "definition"])
        cv = load(f"cv-{key}")["paired"].set_index(["metric", "definition", "contrast"])
        row = {"scenario": key, "label": label}
        for q in (
            "dll: age",
            "dll: interests",
            "dll: lifestyle",
            "diff: lifestyle - interests",
            "diff: lifestyle - age",
            "diff: lifestyle - age+interests",
            "ratio: lifestyle / interests",
            "share: age",
        ):
            for d in ("mean", "last") if not q.startswith("share") else ("mean",):
                r = t.loc[(q, d)]
                row[f"{q} [{d}]"] = r["estimate"]
                row[f"{q} [{d}] lo"], row[f"{q} [{d}] hi"] = r["ci_low"], r["ci_high"]
                row[f"{q} [{d}] excludes0"] = bool(r["excludes_zero"])
        g = cv.loc[("logloss", "last", "gain: lifestyle")]
        row["cv dlogloss lifestyle last"] = g["estimate"]
        row["cv dlogloss lifestyle last lo"] = g["ci_low"]
        row["cv dlogloss lifestyle last hi"] = g["ci_high"]
        rows.append(row)
    sens = pd.DataFrame(rows).set_index("scenario", drop=False)
    sens.to_csv(OUT / "dictionary_sensitivity.csv", index=False)

    ch_rows = []
    for key in ("ii", "iii", "iv", "vi"):
        per = {}
        for c in CLUSTERS:
            oa, ba = draws["i"][c]
            ob, bb = draws[key][c]
            per[c] = h1_rebase.summarise_change(oa, ba, ob, bb)
        ch = h1_rebase.conservative_ci(per["sender"], per["receiver"])
        ch.insert(0, "scenario", key)
        ch_rows.append(ch)
    change = pd.concat(ch_rows)
    change.to_csv(OUT / "dictionary_change_vs_v0.csv", index=False)

    order = ("i", "iii", "iv", "ii", "vi")
    names = {
        "i": "v0: mapowanie agenta",
        "iii": "tylko mapowanie surowych tagów (A)",
        "iv": "tylko kategorie hobby/styl życia (B)",
        "ii": "A + B",
        "vi": "v1: A + B + scalenia tagów",
    }
    q = "ratio: lifestyle / interests [mean]"
    plot = pd.DataFrame(
        {
            "scenario": [names[k] for k in order],
            "estimate": [sens.loc[k, q] for k in order],
            "ci_low": [sens.loc[k, q + " lo"] for k in order],
            "ci_high": [sens.loc[k, q + " hi"] for k in order],
            "baseline": [k == "i" for k in order],
        }
    )
    plot.to_csv(OUT / "dictionary_ratio_plot_data.csv", index=False)
    covers_one = bool(((plot["ci_low"] <= 1) & (plot["ci_high"] >= 1)).all())
    chv = change[
        (change["scenario"] == "vi")
        & (change["quantity"] == "ratio: lifestyle / interests")
        & (change["definition"] == "mean")
    ].iloc[0]

    def pl(x: float) -> str:
        return f"{x:.2f}".replace(".", ",")

    parts = []
    if covers_one:
        parts.append("Każdy przedział obejmuje 1: dane nie rozstrzygają, co wnosi więcej.")
    parts.append(
        f"Zmiana względem v0 (v1 − v0, liczona parami): {pl(chv['estimate'])} "
        f"[{pl(chv['ci_low'])}; {pl(chv['ci_high'])}], przedział "
        f"{'nie ' if chv['excludes_zero'] else ''}obejmuje zera."
    )
    note = " ".join(parts)
    (OUT / "dictionary_ratio_plot_note.txt").write_text(note + "\n", encoding="utf-8")
    h1_rebase.plot_dictionary_sensitivity(plot, OUT / "dictionary_sensitivity.png", note=note)

    # 12 scenarios and the v0 -> v1 table -----------------------------------------------------
    for key, tag in (("i", "v0"), ("vi", "v1")):
        try:
            sensitivity12(key).to_csv(OUT / f"sensitivity12_{tag}.csv", index=False)
        except FileNotFoundError as err:  # sensitivity jobs not finished yet
            print(f"sensitivity12 {tag} skipped: {err}")
    n0, n1 = reported_numbers("i"), reported_numbers("vi")
    key_cols = ["section", "quantity"]
    merged = n0.merge(n1, on=key_cols, suffixes=("_v0", "_v1"), how="outer")
    merged.to_csv(OUT / "v0_v1_reported_numbers.csv", index=False)
    print(sens.T.to_string())
    print(change[change["definition"] == "mean"].to_string())


def decompose_tags() -> None:
    """Z4: one refit per tag decision moved relative to v0 (pooled logit, same controls)."""
    OUT.mkdir(parents=True, exist_ok=True)
    base_map, agent_cat, _ = d1.load_tag_mappings(
        DOCS / "interests_mapping.csv", DOCS / "tag_category_proposal.csv"
    )
    final_cat = tv.load_consensus_b(TAGVAL / "consensus_B.csv")
    cons_a = tv.load_consensus_a(TAGVAL / "consensus_A.csv", base_map)
    merge = tv.load_merge_map(TAGVAL / "tag_merge_map.csv")
    v0 = tv.with_city_dummies(pd.read_parquet(DATA / h1_v1.V0_FILE))
    mask = v0[h1._spec_required_cols(h1.H1Spec())].notna().all(axis=1)
    base_metrics = tv.fit_metrics(v0)

    tags = [
        "cooking",
        "instruments",
        "vanlife",
        "long_talks",
        "city_breaks",
        "healthy_food",
        "marketing_social",
        "tech_it",
    ]
    shifts = h1_rebase.single_category_shifts(tags, agent_cat, final_cat)
    shifts += h1_rebase.single_merge_shifts(merge)
    biz = {r: c for r, c in cons_a.items() if c == "bussiness"}
    calm = {r: c for r, c in cons_a.items() if c == "likes_calm"}
    new = {r: c for r, c in cons_a.items() if r not in biz and r not in calm}
    for label, part in (
        ("A: biznes/startupy → bussiness (3 surowe)", biz),
        ("A: „Lubię spokój” → likes_calm", calm),
        ("A: 4 surowe tagi bez wpisu → active_sport, works_remote, quiet_evenings, diy", new),
        ("A: wszystkie 8 nadpisań", cons_a),
    ):
        shifts.append(
            h1_rebase.Shift(label, {"raw_to_canonical_override": part}, "mapowanie surowych tagów")
        )
    shifts.append(
        h1_rebase.Shift(
            "B: wszystkie zmiany kategorii (5)", {"category_override": final_cat}, "kategorie"
        )
    )
    shifts.append(
        h1_rebase.Shift("scalenia: wszystkie 5", variant_kwargs_merge_only(merge), "scalenia")
    )
    shifts.append(h1_rebase.Shift("v1 = A + B + scalenia", variant_kwargs("vi"), "wszystko"))
    out = h1_rebase.decompose(shifts, base_metrics, v0, mask, DATA, DOCS)
    out["ratio_v0"] = base_metrics["lifestyle_to_interests_ratio"]
    out.to_csv(OUT / "decomposition.csv", index=False)
    print(out.round(3).to_string())


def variant_kwargs_merge_only(merge: dict) -> dict:
    d13, _ = tv.rekey_d13_map(dict(d1.TAG_TO_STRUCTURED_FIELD_MAP), merge)
    pairs, _ = tv.remap_polarity_pairs([(set(p), set(n)) for p, n in d1.POLARITY_PAIRS], merge)
    return {"tag_merge": merge, "d13_map": d13, "polarity_pairs": pairs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--stage", choices=("compute", "decompose", "aggregate", "all"), default="all")
    a = ap.parse_args()
    if a.stage in ("compute", "all"):
        compute(a.workers)
    if a.stage in ("decompose", "all"):
        decompose_tags()
    if a.stage in ("aggregate", "all"):
        aggregate()


if __name__ == "__main__":
    main()
