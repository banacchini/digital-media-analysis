"""H3a level 3: diagnostics (block A), standard errors for the GLMM (block B).

Everything here reuses the cached fits of levels 1-2 (`analysis.fit_models`) and writes
aggregates only. Block A is post hoc diagnostics prompted by S2a (except S8, which was planned);
no multiplicity correction and no confirmatory claims.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.special import expit

from rentfriends.h3a import analysis as A
from rentfriends.h3a import classify as C
from rentfriends.h3a import models as M
from rentfriends.h3a import stats3 as S

POST_HOC = "diagnostyka post hoc, zainicjowana wynikiem S2a (bez poprawek na wielokrotność)"

# Rows of figure C (order = display order, top to bottom): key, plain-language label.
FIG_C_ROWS = [
    ("main", "model podstawowy"),
    ("S1", "tylko aktywni użytkownicy"),
    ("S2a", "tylko swipe'y z pewną wersją profilu"),
    ("S2b", "cechy z aktualnych profili"),
    ("S3", "z kontami z Hyderabadu"),
    ("S4", "inna miara kompletności profilu"),
    ("S5", "bio < 10 znaków uznane za puste"),
    ("S6", "surowa liczba zainteresowań"),
    ("S7", "więcej cech profilu w modelu"),
    ("S8_F", "tylko kobiety oceniają"),
    ("S8_M", "tylko mężczyźni oceniają"),
]


def _spec_frames(ctx: A.Ctx) -> dict[str, tuple[pd.DataFrame, M.Spec]]:
    """(data, spec) for the main model, S1-S7 and the S8 strata, keyed as in the fit cache."""
    out = {"main": (ctx.main, M.Spec())}
    out |= A.sensitivity_samples(ctx)
    for sx in ("F", "M"):
        out[f"S8_{sx}"] = (ctx.main[ctx.main["sender_sex"] == sx], M.Spec(name=f"S8_{sx}"))
    return out


def _m2_parts(ctx: A.Ctx, key: str, df: pd.DataFrame, spec: M.Spec):
    """Cached M2 fit plus the design matrix it was fitted on."""
    out = A.fit_models(ctx, key, df, spec, which=("M2",))
    r = out["M2"]
    X, *_ = A._arrays(df, spec)
    return r, X


# ============================================================================ A5


def a5_probs(ctx: A.Ctx) -> dict:
    """Standardised P(right swipe) at has_bio = 0/1 (F, M, all) and AME for every spec."""
    frames = _spec_frames(ctx)
    res: dict = {"label": "A5", "strata": {}, "by_spec": []}
    with ctx.runner.step("A5_probs"):
        for name, key in (("all", "main"), ("F", "S8_F"), ("M", "S8_M")):
            df, spec = frames[key]
            r, X = _m2_parts(ctx, key, df, spec)
            j = r["names"].index("has_bio")
            sp = S.standardized_probs(X, np.array(r["coef"]), np.array(r["cov"]), j)
            sp["n_senders"] = int(df["s_key"].nunique())
            sp["n_receivers"] = int(df["r_key"].nunique())
            res["strata"][name] = sp
        res["strata"]["O"] = {"skipped": ctx.res["s8"]["strata"].get("O", {}).get("skipped", "")}
        for key, label in FIG_C_ROWS:
            df, spec = frames[key]
            r, X = _m2_parts(ctx, key, df, spec)
            beta = np.array(r["coef"])
            j = r["names"].index("has_bio")
            ame = r["ame"]
            row = {
                "spec": key,
                "label": label,
                "n_obs": len(df),
                "ame_m2": ame,
                "or_m2": ctx.res["fits"][key]["M2"],
            }
            row.pop("or_m2")
            # M3 (sender FE) expressed on the same scale: baseline risks from M2 at has_bio = 0.
            r3 = ctx.res["fits"][key].get("M3") or {}
            b3, se3 = M.coef_of(r3, "has_bio")
            if math.isfinite(b3) and math.isfinite(se3) and r3.get("status") == "ok":
                X0 = X.copy()
                X0[:, j] = 0.0
                p0 = expit(X0 @ beta)
                row["m3_pp"] = {
                    "pct": S.translate_beta_to_pp(p0, b3),
                    "lo95": S.translate_beta_to_pp(p0, b3 - C.Z95 * se3),
                    "hi95": S.translate_beta_to_pp(p0, b3 + C.Z95 * se3),
                }
            else:
                row["m3_pp"] = None
            res["by_spec"].append(row)
    ctx.res["a5"] = res
    _save_a5_tables(ctx, res)
    A.persist(ctx)
    return res


def _save_a5_tables(ctx: A.Ctx, res: dict) -> None:
    rows = []
    for name, sp in res["strata"].items():
        if "p0" not in sp:
            continue
        rows.append(
            {
                "warstwa": name,
                "n_swipes": sp["n"],
                "n_senders": sp["n_senders"],
                "p_bez_bio_pct": sp["p0"]["pct"],
                "p_bez_bio_lo95": sp["p0"]["lo95"],
                "p_bez_bio_hi95": sp["p0"]["hi95"],
                "p_z_bio_pct": sp["p1"]["pct"],
                "p_z_bio_lo95": sp["p1"]["lo95"],
                "p_z_bio_hi95": sp["p1"]["hi95"],
                "roznica_pp": sp["diff"]["pct"],
                "roznica_lo95": sp["diff"]["lo95"],
                "roznica_hi95": sp["diff"]["hi95"],
                "na_100_bez_bio": sp["per100_p0"],
                "na_100_z_bio": sp["per100_p1"],
            }
        )
    ctx.saver.save_table(pd.DataFrame(rows), "h3a_a5_standardized_probs")
    rows = []
    for r in res["by_spec"]:
        m3 = r["m3_pp"] or {}
        rows.append(
            {
                "spec": r["spec"],
                "n_obs": r["n_obs"],
                "ame_m2_pp": r["ame_m2"]["ame_pp"],
                "ame_m2_lo95": r["ame_m2"]["lo95_pp"],
                "ame_m2_hi95": r["ame_m2"]["hi95_pp"],
                "m3_przeliczone_pp": m3.get("pct"),
                "m3_lo95": m3.get("lo95"),
                "m3_hi95": m3.get("hi95"),
            }
        )
    ctx.saver.save_table(pd.DataFrame(rows), "h3a_a5_ame_by_spec")
