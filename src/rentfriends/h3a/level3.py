"""H3a level 3: diagnostics (block A), standard errors for the GLMM (block B).

Everything here reuses the cached fits of levels 1-2 (`analysis.fit_models`) and writes
aggregates only. Block A is post hoc diagnostics prompted by S2a (except S8, which was planned);
no multiplicity correction and no confirmatory claims.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pandas as pd
from scipy.special import expit

from rentfriends.h3a import analysis as A
from rentfriends.h3a import classify as C
from rentfriends.h3a import models as M
from rentfriends.h3a import stats3 as S
from rentfriends.h3a.runner import fingerprint

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


# ============================================================================ GLMM single fit

GLMM_CONFIGS: tuple[tuple[str, dict], ...] = (
    ("lbfgs", {}),
    ("gradient_descent", {}),
    ("gradient_descent", {"delta_rel_conv": 1e-8}),
    ("lbfgs", {"delta_rel_conv": 1e-8}),
)


def glmm_once(
    X: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    receiver: np.ndarray,
    names: list[str],
    optimizer: str,
    extra: dict,
    offset: np.ndarray | None = None,
    std_err: bool = True,
) -> dict:
    """One GPBoost fit with one optimizer configuration (no fallback chain).

    Returns coefficients, variances, log-likelihood (Laplace), GPBoost convergence code, time.
    SEs are attempted only when `std_err` is set; failures are recorded, not raised.
    """
    import warnings

    import gpboost as gpb

    t0 = time.time()
    m = gpb.GPModel(group_data=np.column_stack([sender, receiver]), likelihood="bernoulli_logit")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(y=y, X=X, params={"optimizer_cov": optimizer, **extra}, offset=offset)
    res = {
        "optimizer": optimizer + (f" {extra}" if extra else ""),
        "convergence_status": int(m._get_convergence_status()),
        "n_iter": int(m._get_num_optim_iter()),
        "time_s": time.time() - t0,
        "names": list(names),
        "loglik": -float(m.get_current_neg_log_likelihood()),
    }
    coef = m.get_coef()
    res["coef"] = np.asarray(coef, float).ravel().tolist()
    cov = np.asarray(m.get_cov_pars(), float).ravel()
    res["var_sender"], res["var_receiver"] = float(cov[0]), float(cov[1])
    res["se"] = None
    if std_err:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                c2 = m.get_coef(std_err=True).to_numpy()
            res["se"] = c2[1].tolist()
        except Exception as e:  # noqa: BLE001
            res["se_error"] = str(e)[:200]
    res["status"] = "ok" if res["convergence_status"] == 0 else "not_converged"
    return res


# ============================================================================ A1


def a1_all_attempts(ctx: A.Ctx) -> dict:
    """Refit every optimizer configuration of D-H3a-9 on the main spec and keep all results."""
    X, y, s, r, names, _ = A._arrays(ctx.main, M.Spec())
    rows = []
    with ctx.runner.step("A1_attempts"):
        for i, (opt, extra) in enumerate(GLMM_CONFIGS):
            fp = fingerprint(X, y, s, r, extra={"a1": i, "opt": opt, "extra": extra})
            res = ctx.runner.fit(f"A1__{i}", glmm_once, X, y, s, r, names, opt, extra, fp=fp)
            j = names.index("has_bio")
            rows.append(
                {
                    "config": res.get("optimizer", f"{opt} {extra}"),
                    "status": res.get("status"),
                    "convergence_code": res.get("convergence_status"),
                    "beta_has_bio": res["coef"][j] if res.get("coef") else None,
                    "var_sender": res.get("var_sender"),
                    "var_receiver": res.get("var_receiver"),
                    "loglik": res.get("loglik"),
                    "se_has_bio": (res.get("se") or [None] * len(names))[j],
                    "time_s": res.get("time_s", res.get("_wall_s")),
                }
            )
    tab = pd.DataFrame(rows)
    ctx.saver.save_table(tab, "h3a_a1_glmm_attempts")
    m3 = ctx.res["fits"]["main"]["M3"]
    m2 = ctx.res["fits"]["main"]["M2"]
    out = {
        "label": "A1",
        "post_hoc": POST_HOC,
        "attempts": rows,
        "beta_m2": M.coef_of(m2, "has_bio")[0],
        "beta_m3": M.coef_of(m3, "has_bio")[0],
    }
    conv = [r_ for r_ in rows if r_["convergence_code"] == 0 and r_["beta_has_bio"] is not None]
    out["beta_range_converged"] = (
        [min(r_["beta_has_bio"] for r_ in conv), max(r_["beta_has_bio"] for r_ in conv)]
        if conv
        else None
    )
    ctx.res["a1"] = out
    A.persist(ctx)
    return out


# ============================================================================ A2


def _interaction(r: dict, terms: list[str]) -> dict:
    """Wald test of interaction terms from a fit with `cov`."""
    if not r or "cov" not in r:
        return {"status": "no_cov"}
    names = r["names"]
    idx = [names.index(t) for t in terms if t in names]
    if len(idx) != len(terms):
        return {"status": "terms_missing"}
    b = np.array(r["coef"])[idx]
    V = np.array(r["cov"])[np.ix_(idx, idx)]
    if not np.all(np.isfinite(V)):
        return {"status": "nonfinite"}
    return {"status": "ok", "terms": terms, "coef": b.tolist()} | S.wald_chi2(b, V)


def _ci_row(key: str, model: str, r: dict, margin: float, **extra) -> dict:
    row = A.bio_row(key, model, r, margin)
    row |= extra
    return {
        k: row.get(k)
        for k in ("spec", "model", "status", "or", "or_lo95", "or_hi95", "p", "label", *extra)
    }


def a2_heterogeneity(ctx: A.Ctx) -> dict:
    """Does the has_bio association depend on feature provenance or on account/profile age?"""
    margin = ctx.p.margin
    main = ctx.main.copy()
    first_day = ctx.raw.history.groupby("user_key")["day"].min()
    main["asof_prior"] = (main["asof_source"] == "prior_version").astype(float)
    main["sender_account_age_days"] = main["day"] - main["s_key"].map(first_day)
    main["receiver_profile_age_days"] = main["day"] - main["r_key"].map(first_day)
    res: dict = {"label": "A2", "post_hoc": POST_HOC, "bins": S.AGE_BIN_LABELS}
    rows: list[dict] = []
    with ctx.runner.step("A2_heterogeneity"):
        # --- provenance of as-of features
        out = A.fit_models(
            ctx,
            "A2_asof_int",
            main,
            M.Spec(name="A2_asof", interact_cols=("asof_prior",)),
            which=("M2", "M3"),
        )
        res["asof_interaction"] = {
            m: _interaction(out[m], ["has_bio:asof_prior"]) for m in ("M2", "M3")
        }
        comp = main[main["asof_prior"] == 0]
        prior = main[main["asof_prior"] == 1]
        o_prior = A.fit_models(ctx, "S2a", prior, M.Spec(name="S2a"), which=("M2", "M3"))
        o_comp = A.fit_models(ctx, "A2_asof_comp", comp, M.Spec(name="A2_comp"), which=("M2", "M3"))
        for grp, o, n in (
            ("prior_version", o_prior, len(prior)),
            ("first_version / users_current", o_comp, len(comp)),
        ):
            for m in ("M2", "M3"):
                rows.append(_ci_row("asof", m, o[m], margin, grupa=grp, n_obs=n))
        # --- account / profile age (users without history excluded and counted)
        has_hist = (
            main["sender_account_age_days"].notna() & main["receiver_profile_age_days"].notna()
        )
        no_hist_users = set(ctx.raw.users["user_key"]) - set(ctx.raw.history["user_key"])
        ana = main[has_hist].copy()
        res["excluded_no_history"] = {
            "rows": int((~has_hist).sum()),
            "users_in_main_sample": int(
                len(
                    (set(main.loc[~has_hist, "s_key"]) | set(main.loc[~has_hist, "r_key"]))
                    & no_hist_users
                )
            ),
        }
        for side, col, tag in (
            ("nadawca", "sender_account_age_days", "sb"),
            ("odbiorca", "receiver_profile_age_days", "rb"),
        ):
            ana[f"{tag}_bin"] = S.age_bin(ana[col])
            ana[f"{tag}_1_7"] = (ana[f"{tag}_bin"] == "1-7").astype(float)
            ana[f"{tag}_ge8"] = (ana[f"{tag}_bin"] == "≥ 8").astype(float)
            out = A.fit_models(
                ctx,
                f"A2_{tag}_int",
                ana,
                M.Spec(name=f"A2_{tag}", interact_cols=(f"{tag}_1_7", f"{tag}_ge8")),
                which=("M2", "M3"),
            )
            res[f"{tag}_interaction"] = {
                m: _interaction(out[m], [f"has_bio:{tag}_1_7", f"has_bio:{tag}_ge8"])
                for m in ("M2", "M3")
            }
            res[f"{tag}_composition"] = {
                b: int((ana[f"{tag}_bin"] == b).sum()) for b in S.AGE_BIN_LABELS
            }
            for b in S.AGE_BIN_LABELS:
                sub = ana[ana[f"{tag}_bin"] == b]
                key = f"A2_{tag}_{b.replace(' ', '').replace('≥', 'ge')}"
                o = A.fit_models(ctx, key, sub, M.Spec(name=key), which=("M2", "M3"))
                for m in ("M2", "M3"):
                    rows.append(_ci_row(f"wiek_{side}", m, o[m], margin, grupa=b, n_obs=len(sub)))
                    rows[-1]["n_senders"] = int(sub["s_key"].nunique())
    tab = pd.DataFrame(rows)
    res["rows"] = tab.to_dict("records")
    ctx.saver.save_table(tab, "h3a_a2_heterogeneity")
    ctx.res["a2"] = res
    A.persist(ctx)
    return res


# ============================================================================ A3

A3_STEPS = [
    ("none", "samo bio"),
    ("demog", "+ płeć, wiek, miasto pary"),
    ("demog_completeness", "+ kompletność profilu"),
    ("full", "+ liczba zainteresowań (model główny)"),
]


def a3_stepwise(ctx: A.Ctx) -> dict:
    """OR of has_bio as controls are added (same rows in every step)."""
    rows = []
    with ctx.runner.step("A3_stepwise"):
        for cs, label in A3_STEPS:
            key = "main" if cs == "full" else f"A3_{cs}"
            spec = M.Spec() if cs == "full" else M.Spec(name=key, control_set=cs)
            out = A.fit_models(ctx, key, ctx.main, spec, which=("M2", "M3"))
            for m in ("M2", "M3"):
                rows.append(_ci_row(cs, m, out[m], ctx.p.margin, krok=label))
    tab = pd.DataFrame(rows)
    ctx.saver.save_table(tab, "h3a_a3_stepwise")
    ctx.res["a3"] = {"label": "A3", "post_hoc": POST_HOC, "rows": tab.to_dict("records")}
    A.persist(ctx)
    return ctx.res["a3"]


# ============================================================================ A4


def a4_evalues(ctx: A.Ctx) -> dict:
    """E-values (VanderWeele-Ding) for has_bio; RR approximated by sqrt(OR)."""
    rows = []
    for key, grp in (("main", "wszyscy"), ("S8_F", "kobiety"), ("S8_M", "mężczyźni")):
        for m in ("M2", "M3"):
            r = ctx.res["fits"][key].get(m)
            b, se = M.coef_of(r, "has_bio")
            if not (math.isfinite(b) and math.isfinite(se)):
                continue
            w = C.wald_ci(b, se)
            ev = S.e_value_or(w["or"], w["or_lo95"], w["or_hi95"])
            rows.append({"grupa": grp, "model": m, "or": w["or"], **ev})
    tab = pd.DataFrame(rows)
    ctx.saver.save_table(tab, "h3a_a4_evalues")
    ctx.res["a4"] = {
        "label": "A4",
        "post_hoc": POST_HOC,
        "rows": rows,
        "assumption": "RR ≈ sqrt(OR) (wynik częsty, baza ≈ 20%); E = RR + sqrt(RR(RR-1)); "
        "miara czułości, nie dowód braku konfundowania.",
    }
    A.persist(ctx)
    return ctx.res["a4"]


# ============================================================================ B1


def b1_lrt(ctx: A.Ctx, grid_half_width: float = 0.25, grid_points: int = 11) -> dict:
    """Likelihood-ratio test and profile likelihood for beta_has_bio in the crossed GLMM.

    The first optimizer configuration that converges (code 0) both with and without `has_bio`
    is used. The profile fixes beta through an offset (`GPModel.fit(offset=...)`).
    """
    X, y, s, r, names, _ = A._arrays(ctx.main, M.Spec())
    Xn, _, _, _, names_n, _ = A._arrays(ctx.main, M.Spec(drop_bio=True))
    j = names.index("has_bio")
    bio = ctx.main["has_bio"].to_numpy(float)
    res: dict = {"label": "B1", "configs_tried": []}
    with ctx.runner.step("B1_lrt"):
        chosen = None
        for i, (opt, extra) in enumerate(GLMM_CONFIGS):
            fp = fingerprint(X, y, s, r, extra={"b1": "full", "i": i})
            full = ctx.runner.fit(
                f"B1_full__{i}", glmm_once, X, y, s, r, names, opt, extra, fp=fp, std_err=False
            )
            fpn = fingerprint(Xn, y, s, r, extra={"b1": "null", "i": i})
            null = ctx.runner.fit(
                f"B1_null__{i}",
                glmm_once,
                Xn,
                y,
                s,
                r,
                names_n,
                opt,
                extra,
                fp=fpn,
                std_err=False,
            )
            res["configs_tried"].append(
                {
                    "config": full.get("optimizer"),
                    "full_code": full.get("convergence_status"),
                    "null_code": null.get("convergence_status"),
                }
            )
            if full.get("convergence_status") == 0 and null.get("convergence_status") == 0:
                chosen = (i, opt, extra, full, null)
                break
        if chosen is None:
            res["status"] = "no_config_converged_in_both"
            ctx.res["b1"] = res
            A.persist(ctx)
            return res
        i, opt, extra, full, null = chosen
        res["config"] = full["optimizer"]
        res["beta_hat"] = full["coef"][j]
        res["ll_full"], res["ll_null"] = full["loglik"], null["loglik"]
        res["lrt"] = S.lrt(full["loglik"], null["loglik"])
        res["status"] = "ok"
        # profile likelihood on a grid around the estimate (offset = beta * has_bio)
        b_hat = res["beta_hat"]
        grid = list(np.linspace(b_hat - grid_half_width, b_hat + grid_half_width, grid_points))
        keep = [c for c in range(len(names_n))]
        prof = []
        for g, b in enumerate(grid):
            fp = fingerprint(Xn, y, s, r, extra={"b1": "prof", "i": i, "b": round(float(b), 6)})
            f = ctx.runner.fit(
                f"B1_prof__{g:02d}",
                glmm_once,
                Xn[:, keep],
                y,
                s,
                r,
                names_n,
                opt,
                extra,
                fp=fp,
                std_err=False,
                offset=b * bio,
            )
            prof.append(
                {
                    "beta": float(b),
                    "loglik": f.get("loglik"),
                    "code": f.get("convergence_status"),
                }
            )
        ok = [p for p in prof if p["code"] == 0 and p["loglik"] is not None]
        res["profile"] = prof
        res["profile_points_ok"] = len(ok)
        if len(ok) >= 5:
            pts = [(p["beta"], p["loglik"]) for p in ok]
            res["profile_ci"] = S.profile_ci([p[0] for p in pts], [p[1] for p in pts])
            pc = res["profile_ci"]
            res["profile_label"] = C.classify_interval(
                pc["lo90"], pc["hi90"], pc["lo95"], pc["hi95"], ctx.p.margin
            )
    tab = pd.DataFrame(res.get("profile", []))
    if len(tab):
        ctx.saver.save_table(tab, "h3a_b1_profile_likelihood")
    ctx.res["b1"] = res
    A.persist(ctx)
    return res


# ============================================================================ B2


def b2_lme4(ctx: A.Ctx) -> dict:
    """lme4 crossed GLMM with Wald CI (and LRT) for has_bio; classify + M1 = M2 check."""
    res = A.lme4_crosscheck(ctx, with_lrt=True)
    ctx.res["lme4"] = res
    A.persist(ctx)
    return res


# ============================================================================ B3 (optional)


def b3_bootstrap(
    ctx: A.Ctx, n_boot: int = 200, total_timeout_h: float = 3.0, chunk: int = 10
) -> dict:
    """Sender-level bootstrap of beta_has_bio from GPBoost (optional; RUN_BOOTSTRAP=1).

    Each draw resamples senders with replacement (a sender drawn twice becomes two clusters).
    Resampling senders does not reproduce the crossed structure (receivers are shared).
    Partial results are cached every `chunk` replicates.
    """
    import json

    X, y, s, r, names, _ = A._arrays(ctx.main, M.Spec())
    j = names.index("has_bio")
    path = ctx.runner.cache_dir / "B3_bootstrap.json"
    fp = fingerprint(X, y, s, r, extra={"b3": n_boot, "seed": ctx.p.seed})
    state = {"fp": fp, "betas": [], "failed": 0}
    if path.exists():
        old = json.loads(path.read_text())
        if old.get("fp") == fp:
            state = old
    rng = np.random.default_rng(ctx.p.seed + 303)
    senders = np.unique(s)
    rows_of = {u: np.flatnonzero(s == u) for u in senders}
    t0 = time.time()
    done = len(state["betas"]) + state["failed"]
    with ctx.runner.step("B3_bootstrap"):
        for b in range(done, n_boot):
            if time.time() - t0 > total_timeout_h * 3600:
                break
            draw = rng.choice(senders, size=len(senders), replace=True)
            idx = np.concatenate([rows_of[u] for u in draw])
            new_s = np.concatenate([np.full(len(rows_of[u]), k) for k, u in enumerate(draw)])
            try:
                f = glmm_once(X[idx], y[idx], new_s, r[idx], names, "lbfgs", {}, std_err=False)
                if f["convergence_status"] == 0:
                    state["betas"].append(f["coef"][j])
                else:
                    state["failed"] += 1
            except Exception:  # noqa: BLE001
                state["failed"] += 1
            if (b + 1) % chunk == 0:
                path.write_text(json.dumps(state))
    path.write_text(json.dumps(state))
    betas = np.array(state["betas"])
    res = {"label": "B3", "n_ok": int(len(betas)), "n_failed": state["failed"], "status": "ok"}
    if len(betas) >= 30:
        res |= {
            "se": float(betas.std(ddof=1)),
            "ci95": np.percentile(betas, [2.5, 97.5]).tolist(),
            "ci90": np.percentile(betas, [5, 95]).tolist(),
            "mean": float(betas.mean()),
        }
        lo90, hi90 = res["ci90"]
        lo95, hi95 = res["ci95"]
        res["label_pct"] = C.classify_interval(lo90, hi90, lo95, hi95, ctx.p.margin)
    else:
        res["status"] = "too_few_replicates"
    res["caveat"] = "resampling nadawców nie odtwarza w pełni struktury skrzyżowanej"
    ctx.res["b3"] = res
    A.persist(ctx)
    return res


# ============================================================================ B report


def b_report(ctx: A.Ctx) -> dict:
    """Ladder table and the M1 = M2 agreement check where an M1-type interval exists."""
    margin = ctx.p.margin
    m2 = A.bio_row("main", "M2", ctx.res["fits"]["main"]["M2"], margin)
    lab_m2 = m2["label"]
    rows, intervals = [], {}
    b1 = ctx.res.get("b1") or {}
    if b1.get("status") == "ok":
        rows.append(
            {
                "szczebel": "B1 LRT (GPBoost)",
                "co_uzyskano": "test istotności (nie równoważności)",
                "beta": b1["beta_hat"],
                "se_lub_p": f"p = {b1['lrt']['p']:.4f}",
                "ci": "–",
                "status": f"χ² = {b1['lrt']['stat']:.2f}",
            }
        )
        if "profile_ci" in b1:
            pc = b1["profile_ci"]
            rows.append(
                {
                    "szczebel": "B1 profil wiarygodności",
                    "co_uzyskano": "CI z profilu",
                    "beta": b1["beta_hat"],
                    "se_lub_p": "–",
                    "ci": f"95%: {pc['lo95']:.3f} do {pc['hi95']:.3f}",
                    "status": b1.get("profile_label", ""),
                }
            )
            intervals["GPBoost (profil)"] = b1.get("profile_label")
    l4 = ctx.res.get("lme4") or {}
    if l4.get("status") == "ok":
        w = l4["has_bio_wald"]
        rows.append(
            {
                "szczebel": "B2 lme4 (Wald)",
                "co_uzyskano": "β, SE, CI Walda",
                "beta": w["beta"],
                "se_lub_p": f"SE = {w['se']:.4f}",
                "ci": f"95% OR: {w['or_lo95']:.3f}–{w['or_hi95']:.3f}",
                "status": l4["label"],
            }
        )
        intervals["lme4"] = l4["label"]
    else:
        rows.append(
            {
                "szczebel": "B2 lme4",
                "co_uzyskano": "brak",
                "beta": None,
                "se_lub_p": "–",
                "ci": "–",
                "status": l4.get("status", "nie uruchomiono"),
            }
        )
    b3 = ctx.res.get("b3") or {}
    if b3.get("status") == "ok":
        intervals["bootstrap"] = b3["label_pct"]
        rows.append(
            {
                "szczebel": "B3 bootstrap po nadawcach",
                "co_uzyskano": "SE i percentylowe CI",
                "beta": b3["mean"],
                "se_lub_p": f"SE = {b3['se']:.4f}",
                "ci": f"95%: {b3['ci95'][0]:.3f} do {b3['ci95'][1]:.3f}",
                "status": b3["label_pct"],
            }
        )
    tab = pd.DataFrame(rows)
    ctx.saver.save_table(tab, "h3a_b_ladder")
    agreement = {
        k: {"label_m1": v, "label_m2": lab_m2, "zgodne": v == lab_m2} for k, v in intervals.items()
    }
    rep = {"ladder": rows, "label_m2": lab_m2, "agreement": agreement}
    # estimator check GPBoost vs lme4 (point estimates and variances)
    a1 = ctx.res.get("a1") or {}
    if l4.get("status") == "ok" and a1.get("attempts"):
        conv = [a for a in a1["attempts"] if a["convergence_code"] == 0]
        if conv:
            g = conv[0]
            bl = M.coef_of(l4, "has_bio")[0]
            rep["estimator_check"] = {
                "beta_gpboost": g["beta_has_bio"],
                "beta_lme4": bl,
                "var_sender": [g["var_sender"], l4["var_sender"]],
                "var_receiver": [g["var_receiver"], l4["var_receiver"]],
                "rozbieznosc": abs(g["beta_has_bio"] - bl) > 0.05,
            }
    ctx.res["b_report"] = rep
    A.persist(ctx)
    return rep


# ============================================================================ C4, C5 (preprint)


def _pl(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def _or_axis(ax, lo: float, hi: float) -> None:
    ticks = [t for t in (0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75) if lo <= t <= hi] or [1.0]
    ax.set_xscale("log")
    ax.set_xticks(ticks, [_pl(t, 2).rstrip("0").rstrip(",") for t in ticks])
    ax.minorticks_off()


def preprint_figs(ctx: A.Ctx) -> None:
    """C4: coefficient stability when controls are added; C5: heterogeneity (A2)."""
    import matplotlib.pyplot as plt

    from rentfriends.h3a import theme as T

    T.apply_theme()
    col = T.COLORS
    margin = ctx.p.margin
    n_main, n_rec = len(ctx.main), ctx.main["r_key"].nunique()

    def draw_row(ax, y, row, model):
        if not row or row.get("or") is None or not math.isfinite(row["or"]):
            return False
        c = col["with_bio"] if model == "M2" else col["text"]
        ax.hlines(y, row["or_lo95"], row["or_hi95"], color=c, lw=2.5)
        ax.plot(
            row["or"],
            y,
            "o" if model == "M2" else "D",
            ms=11,
            mfc=c if model == "M2" else "white",
            mec=c,
            mew=2.2,
            zorder=3,
        )
        return True

    # ---------------------------------------------------------------- C4
    a3 = pd.DataFrame(ctx.res["a3"]["rows"])
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axvspan(math.exp(-margin), math.exp(margin), color=col["muted"], alpha=0.8, lw=0)
    ax.axvline(1, color=col["without_bio"], lw=1.2)
    steps = [lbl for _, lbl in A3_STEPS]
    for i, lbl in enumerate(steps):
        for m, off in (("M2", -0.12), ("M3", 0.14)):
            row = a3[(a3["krok"] == lbl) & (a3["model"] == m)].iloc[0].to_dict()
            if draw_row(ax, i + off, row, m):
                ax.annotate(
                    _pl(row["or"]),
                    (row["or_hi95"], i + off),
                    xytext=(8, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=14,
                )
    ax.set_yticks(range(len(steps)), steps, fontsize=15)
    ax.invert_yaxis()
    _or_axis(ax, 0.95, 1.5)
    ax.set_xlim(0.95, 1.55)
    ax.tick_params(axis="x", labelsize=15)
    ax.set_xlabel("OR prawego swipe'a: bio vs brak bio (skala log)", fontsize=15)
    ax.text(
        0.99,
        1.03,
        "kółko: M2 (wszyscy razem); romb: M3 (w obrębie nadawcy)",
        transform=ax.transAxes,
        ha="right",
        fontsize=14,
    )
    ax.tick_params(length=0)
    ctx.saver.save_fig(
        fig,
        "h3a_09_stabilnosc_kontroli",
        a3[["spec", "model", "krok", "or", "or_lo95", "or_hi95", "p", "label"]],
        caption="Rys. C4. Stabilność OR dla has_bio po kolejnym dodawaniu kontroli (ta sama "
        "próba w każdym kroku; M2 i M3; 95% CI). Diagnostyka post hoc.",
        model="A3 (M2, M3)",
        n_swipes=n_main,
        n_receivers=n_rec,
    )
    plt.close(fig)

    # ---------------------------------------------------------------- C5
    a2 = ctx.res["a2"]
    rows = pd.DataFrame(a2["rows"])
    sections = [
        ("asof", "Pochodzenie cech profilu", ["prior_version", "first_version / users_current"]),
        ("wiek_nadawca", "Dzień konta nadawcy", S.AGE_BIN_LABELS),
        ("wiek_odbiorca", "Wiek profilu odbiorcy (dni)", S.AGE_BIN_LABELS),
    ]
    inter_key = {"asof": "asof_interaction", "wiek_nadawca": "sb_interaction"}
    inter_key["wiek_odbiorca"] = "rb_interaction"
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.axvspan(math.exp(-margin), math.exp(margin), color=col["muted"], alpha=0.8, lw=0)
    ax.axvline(1, color=col["without_bio"], lw=1.2)
    y, ticks, labels, hdr = 0.0, [], [], []
    for spec, title, groups in sections:
        it = a2[inter_key[spec]]
        txt = f"{title}; test interakcji p = " + " / ".join(
            f"{_pl(it[m]['p'], 3)} ({m})" for m in ("M2", "M3") if it[m].get("status") == "ok"
        )
        hdr.append((y - 0.75, txt))
        for g in groups:
            for m, off in (("M2", -0.12), ("M3", 0.14)):
                sel = rows[(rows["spec"] == spec) & (rows["grupa"] == g) & (rows["model"] == m)]
                row = sel.iloc[0].to_dict()
                ok = draw_row(ax, y + off, row, m)
                if not ok and m == "M3":
                    m2row = rows[
                        (rows["spec"] == spec) & (rows["grupa"] == g) & (rows["model"] == "M2")
                    ].iloc[0]
                    ax.annotate(
                        "M3: brak oszacowania",
                        (m2row["or_hi95"], y),
                        xytext=(12, 0),
                        textcoords="offset points",
                        fontsize=13,
                        color=col["accent_text"],
                        va="center",
                    )
            n = int(sel.iloc[0]["n_obs"])
            ticks.append(y)
            labels.append(f"{g}  (n = {n:,})".replace(",", " "))
            y += 1.0
        y += 1.0
    for yy, txt in hdr:
        ax.text(
            0.0,
            yy,
            txt,
            transform=ax.get_yaxis_transform(),
            fontsize=14,
            fontweight="bold",
            color=col["text"],
            va="center",
        )
    ax.set_yticks(ticks, labels, fontsize=14)
    ax.set_ylim(y - 0.5, -1.5)
    _or_axis(ax, 0.8, 1.7)
    ax.set_xlim(0.8, 1.7)
    ax.tick_params(axis="x", labelsize=15)
    ax.tick_params(length=0)
    ax.set_xlabel("OR prawego swipe'a: bio vs brak bio (skala log)", fontsize=15)
    ax.text(
        0.99,
        0.02,
        "kółko: M2; romb: M3; kreska: 95% CI",
        transform=ax.transAxes,
        ha="right",
        fontsize=13,
    )
    ctx.saver.save_fig(
        fig,
        "h3a_10_heterogenicznosc",
        rows[["spec", "model", "grupa", "n_obs", "or", "or_lo95", "or_hi95", "p", "label"]],
        caption="Rys. C5. OR dla has_bio wg pochodzenia cech profilu (as-of), dnia konta "
        "nadawcy i wieku profilu odbiorcy (kosze 0, 1-7, ≥ 8 dni); M2 i M3, 95% CI. "
        "Diagnostyka post hoc zainicjowana wynikiem S2a, bez poprawek na wielokrotność.",
        model="A2 (M2, M3)",
        n_swipes=n_main,
        n_receivers=n_rec,
    )
    plt.close(fig)


# ============================================================================ driver


def run_level3(ctx: A.Ctx, only: str = "", bootstrap: bool = False) -> list[str]:
    """Level 3 in the order A5 -> figures/numbers -> A1-A4 -> B1 -> B2 -> exports.

    `only`: "" (everything) | diagnostics | se | figures | lme4.
    """
    from pathlib import Path

    from rentfriends.h3a import export3 as E3
    from rentfriends.h3a import story_figs as SF
    from rentfriends.h3a import theme as T

    if only not in ("", "diagnostics", "se", "figures", "lme4"):
        raise ValueError(f"unknown ONLY={only!r}")

    def do(*names: str) -> bool:
        return not only or only in names

    export_dir = Path(ctx.p.report_dir) / "export"
    if do("figures", "diagnostics"):
        a5_probs(ctx)
    if do("figures"):
        ctx.res["story_fig_checks"] = SF.make_all(ctx.res["a5"], FIG_C_ROWS, export_dir)
        T.export_theme_json(export_dir / "theme.json")
    if do("diagnostics"):
        a3_stepwise(ctx)
        a4_evalues(ctx)
        a2_heterogeneity(ctx)
        a1_all_attempts(ctx)
        preprint_figs(ctx)
    if do("se"):
        b1_lrt(ctx)
        b2_lme4(ctx)
        if bootstrap:
            b3_bootstrap(ctx)
    if only == "lme4":
        b2_lme4(ctx)
    if do("se", "lme4"):
        b_report(ctx)
    A.persist(ctx)
    files: list[str] = []
    if "a5" in ctx.res:
        E3.write_numbers(ctx.res, export_dir, T.theme_dict())
        E3.write_captions(ctx.res, export_dir)
        files = sorted(p.name for p in export_dir.iterdir())
        E3.write_summary3(ctx.res, ctx.p.report_dir, files)
    return files
