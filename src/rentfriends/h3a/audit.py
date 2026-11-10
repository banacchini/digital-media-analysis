"""Post-audit additions for H3a (docs/prompts/fix-h3a-prompt-v2.md, tasks Z1-Z5).

Everything here is labelled `post hoc (audyt)`. The pre-registered rule in `classify.py` is not
touched. Heavy fits are cached outside git (`data/interim/h3a/`, key = data hash). Only
aggregates are stored; user keys and bios never leave memory.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from rentfriends import h1_tagval as tv
from rentfriends.h3a import analysis as A
from rentfriends.h3a import classify as C
from rentfriends.h3a import data as D
from rentfriends.h3a import m4
from rentfriends.h3a import models as M
from rentfriends.h3a import variables as v
from rentfriends.h3a.runner import Runner, fingerprint

CACHE_DIR = Path("data/interim/h3a")
OUT_JSON = Path("reports/h3a/audit_results.json")
TAGVAL_DIR = Path("docs/tag-validation")
MIN_CELL = 5


# ----------------------------------------------------------------------------- Z1: label trace


def label_trace(beta: float, se: float, margin: float = 0.10) -> dict:
    """Step-by-step evaluation of the section-7 rule (same logic as `classify.classify`).

    Returns every quantity the rule uses plus the label, so a reader can check by hand why the
    label is what it is. Does not change the rule.
    """
    lo95, hi95 = beta - C.Z95 * se, beta + C.Z95 * se
    lo90, hi90 = beta - C.Z90 * se, beta + C.Z90 * se
    equiv = lo90 >= -margin and hi90 <= margin
    sig_pos = lo95 > 0
    sig_neg = hi95 < 0
    return {
        "beta": beta,
        "se": se,
        "or": math.exp(beta),
        "or_lo95": math.exp(lo95),
        "or_hi95": math.exp(hi95),
        "or_lo90": math.exp(lo90),
        "or_hi90": math.exp(hi90),
        "margin_log": margin,
        "margin_or_lo": math.exp(-margin),
        "margin_or_hi": math.exp(margin),
        "equiv_lo90_ge_minus_margin": lo90 >= -margin,
        "equiv_hi90_le_margin": hi90 <= margin,
        "equiv": equiv,
        "sig_pos_lo95_gt_0": sig_pos,
        "sig_neg_hi95_lt_0": sig_neg,
        # Informational, NOT part of the rule: does the 95% CI exclude the whole margin band?
        "lo95_above_margin": lo95 > margin,
        "label": C.classify(beta, se, margin),
    }


# ----------------------------------------------------------------------------- data


def tag_map_v1(raw: D.RawData, tagval_dir: Path = TAGVAL_DIR) -> dict[str, str]:
    """Tag map with the final human decisions of the tag validation (data contract v1).

    Consensus A overrides the agent mapping of raw strings; merges (`tag_merge_map.csv`) are
    applied to the canonical slugs. Category decisions (consensus B) do not affect H3a, which
    counts all tags regardless of category.
    """
    base = v.build_tag_map(raw.mapping)
    overrides = tv.load_consensus_a(tagval_dir / "consensus_A.csv", base)
    merge = tv.load_merge_map(tagval_dir / "tag_merge_map.csv")
    out = {**base, **overrides}
    out = {k: merge.get(c, c) for k, c in out.items()}
    for k, c in merge.items():
        out.setdefault(k, c)
    return out


def build_main(raw: D.RawData) -> pd.DataFrame:
    """Main analysis sample (no Hyderabad, complete cases) plus the receiver activity proxy."""
    t = D.build_analysis_table(raw).table
    sent = raw.swipes.groupby("user_key").size()
    t["r_activity_log"] = np.log1p(t["r_key"].map(sent).fillna(0).to_numpy(float))
    return D.complete_case(t[t["hyderabad"] == 0])


def receiver_change_sets(raw: D.RawData, receivers: set) -> dict[str, set]:
    """Receivers with any bio text change / empty<->non-empty status change in the history."""
    bh = m4.bio_history(raw.history)
    bh = bh[bh["user_key"].isin(receivers)]
    return {
        "text": set(bh.loc[bh["text_change"], "user_key"]),
        "status": set(bh.loc[bh["status_change"], "user_key"]),
    }


# ----------------------------------------------------------------------------- fits


def _row(key: str, label: str, estimator: str, res: dict | None, margin: float) -> dict:
    r = A.bio_row(key, label, res or {}, margin)
    r["estimator"] = estimator
    if res:
        for k in ("singular", "conv_code", "var_sender", "var_receiver", "lrt_p"):
            if k in res:
                r[k] = res[k]
    return r


def fit_scenario(
    ctx: A.Ctx, key: str, df: pd.DataFrame, spec: M.Spec, lme4: bool = True, which=("M2", "M3")
) -> list[dict]:
    """M2, M3 and (optionally) lme4 for one scenario; returns table rows + sizes."""
    out = A.fit_models(ctx, key, df, spec, which=which)
    rows = [_row(key, m, f"{m} ({_EST[m]})", out.get(m), ctx.p.margin) for m in which]
    if lme4:
        X, y, s, r, names, _ = A._arrays(df, spec)
        assert names[:2] == ["const", "has_bio"], names[:2]
        fp = fingerprint(X, y, s, r, extra={"lme4": True, "names": names})
        res = ctx.runner.fit(
            f"lme4__{key}", A.lme4_fit, X, y, s, r, names, ctx.runner.timeout_s,
            fp=fp, timeout=False,
        )  # fmt: skip
        rows.append(_row(key, "M1_lme4", "M1 (lme4, Wald)", res, ctx.p.margin))
    for rw in rows:
        rw.update(
            n_obs=out["n_obs"],
            n_senders=out["n_senders"],
            n_receivers=out["n_receivers"],
            spec=key,
        )
    return rows


_EST = {
    "M2": "pooled logit, klastrowanie dwukierunkowe",
    "M3": "FE nadawcy, klastrowanie po odbiorcy",
}


def make_ctx(report_dir: Path = CACHE_DIR) -> A.Ctx:
    """Context whose caches live outside git; the committed reports are not touched."""
    report_dir.mkdir(parents=True, exist_ok=True)
    p = A.Params(run_level=3, report_dir=str(report_dir), fit_timeout_min=90.0)
    return A.Ctx(p=p, runner=Runner(report_dir, p.fit_timeout_min), saver=None)  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- scenarios


def _suppress_small(rows: list[dict]) -> list[dict]:
    for r in rows:
        if r.get("n_receivers", 99) < MIN_CELL or r.get("n_senders", 99) < MIN_CELL:
            for k in list(r):
                if k not in ("spec", "model", "estimator"):
                    r[k] = None
            r["label"] = "tłumione (< 5 jednostek)"
    return rows


def load_audit(path: Path = OUT_JSON) -> dict:
    """Read the stored audit results (no recomputation); use this for tables and plots."""
    return json.loads(Path(path).read_text())


def run_audit(
    prior_results: Path = Path("reports/h3a/results.json"), refresh: bool = False
) -> dict:
    """Z1-Z5 on the full sample; writes `reports/h3a/audit_results.json` (aggregates only).

    Two cache layers: every model fit is cached under `data/interim/h3a/cache` (key = data
    hash), and the finished result file is reused unless `refresh=True`. To redo everything
    delete `audit_results.json`; to refit a model delete its file in the cache directory.
    """
    if OUT_JSON.exists() and not refresh:
        return load_audit()
    prior = json.loads(prior_results.read_text())
    margin = prior["params"]["margin"]
    ctx = make_ctx()
    raw = D.load_raw()
    main = build_main(raw)
    res: dict = {"n_main": len(main), "tag_variables_dictionary_dependent": True}

    # --- Z1: label trace for the main models (stored numbers, recomputed from beta and SE).
    mt = {r["model"]: r for r in prior["main_table"]}
    l4 = prior["lme4"]
    res["z1_trace"] = {
        "M2": label_trace(mt["M2"]["beta"], mt["M2"]["se"], margin),
        "M3": label_trace(mt["M3"]["beta"], mt["M3"]["se"], margin),
        "M1_lme4": label_trace(*M.coef_of(l4, "has_bio"), margin),
    }

    # --- Z2: M1 table (lme4 reported; GPBoost point only).
    m1 = prior["fits"]["main"]["M1"]
    b_gp = m1["coef"][m1["names"].index("has_bio")]
    res["z2_table"] = [
        {
            "model": "M1 (lme4, Wald)",
            **{k: l4["has_bio_wald"][k] for k in ("beta", "se", "or", "p")},
            "or_lo95": l4["has_bio_wald"]["or_lo95"],
            "or_hi95": l4["has_bio_wald"]["or_hi95"],
            "or_lo90": l4["has_bio_wald"]["or_lo90"],
            "or_hi90": l4["has_bio_wald"]["or_hi90"],
            "lrt_p": l4.get("lrt_p"),
            "label": l4["label"],
        },
        {
            "model": "M1 (GPBoost, tylko punkt)",
            "beta": b_gp,
            "or": math.exp(b_gp),
            "se": None,
            "label": "brak oszacowania (brak SE)",
        },
        *[{"model": f"{m} ({_EST[m]})", **mt[m]} for m in ("M2", "M3")],
    ]
    res["z2_lme4_diag"] = {
        k: l4[k]
        for k in ("var_sender", "var_receiver", "singular", "conv_code", "r_warnings", "loglik")
    }

    # --- Z3: has_bio by sender sex (exploratory); fits on strata of the main sample.
    z3 = []
    for sx in ("F", "M", "O"):
        df = main[main["sender_sex"] == sx]
        try:
            z3 += fit_scenario(ctx, f"Z3_{sx}", df, M.Spec(name=f"Z3_{sx}"), lme4=(sx != "O"))
        except Exception as e:  # noqa: BLE001
            z3.append({"spec": f"Z3_{sx}", "label": f"nieudane: {type(e).__name__}"})
    res["z3_by_sender_sex"] = _suppress_small(z3)

    # --- Z4: as-of / bio stability.
    ch = receiver_change_sets(raw, set(main["r_key"].unique()))
    rec = set(main["r_key"].unique())
    res["z4_counts"] = {
        "receivers": len(rec),
        "with_text_change": len(ch["text"]),
        "stable_text": len(rec - ch["text"]),
        "with_status_change": len(ch["status"]),
    }
    stable = main[~main["r_key"].isin(ch["text"])]
    nostat = main[~main["r_key"].isin(ch["status"])]
    s2a = main[main["asof_source"] == "prior_version"]
    z4 = []
    z4 += fit_scenario(ctx, "Z4_stable_text", stable, M.Spec(name="Z4_stable_text"))
    z4 += fit_scenario(ctx, "Z4_no_status_change", nostat, M.Spec(name="Z4_no_status"))
    z4 += fit_scenario(ctx, "Z4_S2a_prior_version", s2a, M.Spec(name="Z4_S2a"))
    res["z4"] = z4

    # --- Z5: identification controls.
    z5 = []
    z5 += fit_scenario(
        ctx, "Z5_age_h1", main, M.Spec(name="Z5_age_h1", age_controls="h1"),
    )  # fmt: skip
    z5 += fit_scenario(
        ctx, "Z5_activity", main,
        M.Spec(name="Z5_act", extra_controls=("r_activity_log",)),
    )  # fmt: skip
    z5 += fit_scenario(
        ctx, "Z5_age_h1_activity", main,
        M.Spec(name="Z5_both", age_controls="h1", extra_controls=("r_activity_log",)),
    )  # fmt: skip
    # Tag variables depend on the dictionary: rebuild on data contract v1.
    raw1 = D.load_raw()
    raw1.tag_map_override = tag_map_v1(raw1)
    main1 = build_main(raw1)
    same_rows = len(main1) == len(main)
    cmp = pd.DataFrame(
        {
            "v0": main["tag_count_receiver"].to_numpy(),
            "v1": main1["tag_count_receiver"].to_numpy() if same_rows else np.nan,
        }
    )
    res["z5_tags_v1_check"] = {
        "same_sample_size": same_rows,
        "n_v0": len(main),
        "n_v1": len(main1),
        "share_swipes_tag_count_changed": float((cmp["v0"] != cmp["v1"]).mean())
        if same_rows
        else None,
        "mean_tag_count_v0": float(main["tag_count_receiver"].mean()),
        "mean_tag_count_v1": float(main1["tag_count_receiver"].mean()),
        "tag_zero_changed": int((main["tag_zero"].to_numpy() != main1["tag_zero"].to_numpy()).sum())
        if same_rows
        else None,
        "tag_cap_changed": int((main["tag_cap"].to_numpy() != main1["tag_cap"].to_numpy()).sum())
        if same_rows
        else None,
    }
    z5 += fit_scenario(ctx, "Z5_tags_v1", main1, M.Spec(name="Z5_tags_v1"))
    res["z5"] = z5

    OUT_JSON.write_text(json.dumps(_clean(res), ensure_ascii=False, indent=1))
    return res


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(x) for k, x in o.items()}
    if isinstance(o, list | tuple):
        return [_clean(x) for x in o]
    if isinstance(o, np.floating | float):
        return float(o) if math.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
