"""Estimators for H3a: GLMM (GPBoost), pooled logit with two-way clustering, sender-FE logit.

All fit functions take plain numpy arrays and return JSON-serialisable dicts with aggregated
results only (coefficients, standard errors, variances, timings, status).
"""

from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.special import expit

# ----------------------------------------------------------------------------- design


@dataclass
class Spec:
    """Model specification (main spec = defaults)."""

    name: str = "main"
    bio_var: str = "has_bio"
    completeness_var: str = "profile_completeness"
    tag_vars: tuple[str, str, str] = ("tag_count_receiver", "tag_zero", "tag_cap")
    extended: bool = False  # S7: receiver_age_band + 7 lifestyle values
    bio_terms: str = "binary"  # "binary" | "log_len" | "spline" (M5, on has_bio == 1)
    interaction_sender_sex: bool = False  # S8 interaction test
    drop_bio: bool = False  # M6 baseline
    fe_sender: bool = False  # M3: sex_pair coded as receiver sex within sender sex
    # Level 3: which control blocks enter (A3 sequence): none | demog | demog_completeness | full
    control_set: str = "full"
    # Level 3 (A2): 0/1 columns of the analysis frame entered as main effect + interaction
    # with has_bio.
    interact_cols: tuple[str, ...] = ()
    # Audit (Z5): "signed" = age_band_diff + same_band (main spec); "h1" adds age_band_diff_abs,
    # i.e. the H1 age block (same_band, age_band_diff_abs, age_band_diff).
    age_controls: str = "signed"
    # Audit (Z5): extra standardised numeric columns of the analysis frame (activity proxies).
    extra_controls: tuple[str, ...] = ()
    # Audit (Z8): extra numeric columns entered as they are (not standardised).
    raw_controls: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)


CONT_STD = ["age_band_diff"]  # plus completeness and tag count (spec dependent)
SEX_PAIR_REF = "F→F"
SAME_CITY_REF = "same"


def _dummies(s: pd.Series, prefix: str, ref: str) -> pd.DataFrame:
    d = pd.get_dummies(s.astype("string"), prefix=prefix, prefix_sep="=", dtype=float)
    col = f"{prefix}={ref}"
    # reference absent (e.g. a stratum): drop the most frequent level instead
    return d.drop(columns=col if col in d.columns else d.sum().idxmax())


def _std(x: pd.Series) -> pd.Series:
    sd = x.std()
    return (x - x.mean()) / sd if sd and sd > 0 else x * 0.0


def spline_basis(x: np.ndarray, df: int = 3, design_info=None):
    """Natural cubic regression spline basis (patsy `cr`, centred) and its design info."""
    import patsy

    if design_info is None:
        m = patsy.dmatrix(f"cr(x, df={df}, constraints='center') - 1", {"x": x})
        return np.asarray(m), m.design_info
    (m,) = patsy.build_design_matrices([design_info], {"x": x})
    return np.asarray(m), design_info


def build_design(t: pd.DataFrame, spec: Spec) -> tuple[pd.DataFrame, dict]:
    """Design matrix with an explicit intercept column `const` (GPBoost needs it)."""
    parts: list[pd.DataFrame] = []
    meta: dict = {}
    cols = pd.DataFrame(index=t.index)
    cols["const"] = 1.0
    if not spec.drop_bio:
        if spec.bio_terms == "binary":
            cols["has_bio"] = t[spec.bio_var].astype(float)
        elif spec.bio_terms == "log_len":
            cols["log1p_bio_len"] = np.log1p(t["bio_len"].astype(float))
            cols["bio_len_cap"] = t["bio_len_cap"].astype(float)
        elif spec.bio_terms == "spline":
            b, di = spline_basis(np.log1p(t["bio_len"].to_numpy(float)))
            for j in range(b.shape[1]):
                cols[f"bio_spline_{j}"] = b[:, j]
            cols["bio_len_cap"] = t["bio_len_cap"].astype(float)
            meta["spline_design_info"] = di
    cs = spec.control_set
    if cs != "none":
        cols["age_band_diff"] = _std(t["age_band_diff"].astype(float))
        cols["same_band"] = t["same_band"].astype(float)
        if spec.age_controls == "h1":
            cols["age_band_diff_abs"] = _std(t["age_band_diff"].astype(float).abs())
    for c in spec.extra_controls:
        cols[c] = _std(t[c].astype(float))
    for c in spec.raw_controls:
        cols[c] = t[c].astype(float)
    if cs in ("demog_completeness", "full") and not spec.extended:
        cols[spec.completeness_var] = _std(t[spec.completeness_var].astype(float))
    if cs == "full":
        tc, tz, tcap = spec.tag_vars
        cols[tc] = _std(t[tc].astype(float))
        cols[tz] = t[tz].astype(float)
        cols[tcap] = t[tcap].astype(float)
    for c in spec.interact_cols:
        cols[c] = t[c].astype(float)
        cols[f"has_bio:{c}"] = t["has_bio"].astype(float) * t[c].astype(float)
    parts.append(cols)
    if cs != "none":
        sp = _dummies(t["sex_pair"], "sex_pair", SEX_PAIR_REF)
        if spec.fe_sender:
            # Sender FE absorb the sender-sex main effect; keep only receiver-sex contrasts
            # within each sender sex (reference: receiver F for every sender sex).
            sp = sp[[c for c in sp.columns if not c.endswith("→F")]]
        parts.append(sp)
        parts.append(_dummies(t["same_city"], "same_city", SAME_CITY_REF))
    if spec.extended:
        parts.append(_dummies(t["receiver_age_band"], "receiver_age_band", "18-20"))
        for c in [c for c in t.columns if c.startswith("r_ls_")]:
            parts.append(_dummies(t[c], c[2:], "brak"))
    if spec.interaction_sender_sex:
        for lev in sorted(t["sender_sex"].dropna().unique()):
            if lev == "F":
                continue
            parts.append(
                pd.DataFrame(
                    {
                        f"has_bio:sender_sex={lev}": t["has_bio"].to_numpy(float)
                        * (t["sender_sex"] == lev).to_numpy(dtype=float, na_value=0.0)
                    },
                    index=t.index,
                ).astype(float)
            )
    X = pd.concat(parts, axis=1)
    # Drop constant non-intercept columns (absent levels in subsamples).
    keep = [c for c in X.columns if c == "const" or X[c].std() > 0]
    meta["dropped_constant"] = [c for c in X.columns if c not in keep]
    X = X[keep]
    # Drop binary indicators with complete separation (outcome constant where the indicator
    # is 1): their MLE does not exist and they make the logit Hessian singular. The bio
    # variable itself is never dropped silently.
    y = t["y_right"].to_numpy()
    sep = []
    for c in X.columns:
        if c in ("const", "has_bio"):
            continue
        x = X[c].to_numpy()
        if set(np.unique(x)) <= {0.0, 1.0}:
            yy = y[x == 1]
            if len(yy) and (yy.min() == yy.max()):
                sep.append(c)
    meta["dropped_separated"] = sep
    X = X.drop(columns=sep)
    collinear = collinear_columns(X)
    meta["dropped_collinear"] = collinear
    return X.drop(columns=collinear), meta


def collinear_columns(X: pd.DataFrame, tol: float = 1e-9) -> list[str]:
    """Columns that are exact linear combinations of earlier columns (in column order).

    Uses the Gram matrix: the residual sum of squares of column j on the kept columns is
    XtX[j, j] - XtX[j, S] XtX[S, S]^-1 XtX[S, j]. `const` and `has_bio` come first, so they are
    never dropped in favour of a control.
    """
    A = X.to_numpy(float)
    XtX = A.T @ A
    kept: list[int] = []
    drop = []
    for j in range(A.shape[1]):
        d = XtX[j, j]
        if kept:
            S = np.array(kept)
            b = np.linalg.lstsq(XtX[np.ix_(S, S)], XtX[S, j], rcond=None)[0]
            rss = d - XtX[j, S] @ b
        else:
            rss = d
        if d > 0 and rss > tol * d:
            kept.append(j)
        else:
            drop.append(X.columns[j])
    return drop


def codes(s: pd.Series) -> np.ndarray:
    """Integer codes for a key column (keys never leave memory)."""
    return pd.factorize(s, sort=True)[0].astype(np.int64)


# ----------------------------------------------------------------------------- GLMM


def fit_glmm(
    X: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    receiver: np.ndarray,
    names: list[str],
    optimizers: tuple[tuple[str, dict], ...] = (
        ("lbfgs", {}),
        ("gradient_descent", {}),
        ("gradient_descent", {"delta_rel_conv": 1e-8}),
        ("lbfgs", {"delta_rel_conv": 1e-8}),
    ),
) -> dict:
    """Bernoulli-logit GLMM with crossed sender and receiver random intercepts (Laplace).

    Tries optimizers (and tighter convergence tolerances) in order and stops at the first
    converged fit (GPBoost status 0) with finite SEs; the numerical Hessian behind the SEs is
    sometimes not positive definite at the default tolerance.
    `params={"std_dev": True}` from the prompt is discontinued in GPBoost 1.8; SEs come
    from `get_coef(std_err=True)` / `get_cov_pars(std_err=True)` (D-H3a-9).
    """
    import gpboost as gpb

    attempts = []
    for opt, extra in optimizers:
        t0 = time.time()
        try:
            m = gpb.GPModel(
                group_data=np.column_stack([sender, receiver]), likelihood="bernoulli_logit"
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m.fit(y=y, X=X, params={"optimizer_cov": opt, **extra})
            coef = m.get_coef(std_err=True).to_numpy()
            cov = m.get_cov_pars(std_err=True).to_numpy()
            status = int(m._get_convergence_status())
            res = {
                "optimizer": opt + (f" {extra}" if extra else ""),
                "convergence_status": status,  # 0 ok, 1 max iterations, 2 line search failed
                "n_iter": int(m._get_num_optim_iter()),
                "time_s": time.time() - t0,
                "names": list(names),
                "coef": coef[0].tolist(),
                "se": coef[1].tolist(),
                "var_sender": float(cov[0, 0]),
                "var_receiver": float(cov[0, 1]),
                "var_sender_se": float(cov[1, 0]),
                "var_receiver_se": float(cov[1, 1]),
                "loglik": -float(m.get_current_neg_log_likelihood()),
            }
        except Exception as e:  # noqa: BLE001 - record and try next optimizer
            res = {"optimizer": f"{opt} {extra}", "error": str(e), "time_s": time.time() - t0}
            attempts.append(res)
            continue
        attempts.append({k: res[k] for k in ("optimizer", "convergence_status", "time_s")})
        ok_se = all(math.isfinite(s) for s in res["se"])
        if res["convergence_status"] == 0 and ok_se:
            res["status"] = "ok"
            res["attempts"] = attempts
            return res
    res = dict(res)
    res["status"] = "not_converged_or_no_se"
    res["attempts"] = attempts
    return res


# ----------------------------------------------------------------------------- pooled logit


def _logit_newton(X: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-10):
    beta = np.zeros(X.shape[1])
    for it in range(max_iter):
        p = expit(X @ beta)
        w = p * (1 - p)
        g = X.T @ (y - p)
        H = (X * w[:, None]).T @ X
        step = np.linalg.solve(H, g)
        beta += step
        if np.max(np.abs(step)) < tol:
            return beta, it + 1, True
    return beta, max_iter, False


def cluster_meat(U: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, int]:
    """Sum over clusters of (sum of scores)(sum of scores)'; returns meat and #clusters."""
    g = pd.factorize(groups)[0] if groups.dtype.kind not in "iu" else groups
    G = int(g.max()) + 1
    S = np.zeros((G, U.shape[1]))
    np.add.at(S, g, U)
    return S.T @ S, len(np.unique(g))


def sandwich(bread: np.ndarray, U: np.ndarray, groups: np.ndarray, k: int) -> np.ndarray:
    """CRV1 cluster-robust covariance with Stata-style small-sample correction."""
    n = U.shape[0]
    meat, G = cluster_meat(U, groups)
    c = G / (G - 1) * (n - 1) / (n - k)
    return c * bread @ meat @ bread


def twoway_cov(
    bread: np.ndarray, U: np.ndarray, g1: np.ndarray, g2: np.ndarray, k: int
) -> tuple[np.ndarray, dict]:
    """Cameron-Gelbach-Miller two-way clustering: V1 + V2 - V12 (V12 = intersection).

    If the result is not positive semi-definite, negative eigenvalues are set to zero
    (CGM 2011 suggestion) and flagged.
    """
    inter = pd.factorize(pd.Series(g1).astype(str) + "|" + pd.Series(g2).astype(str))[0]
    V1 = sandwich(bread, U, g1, k)
    V2 = sandwich(bread, U, g2, k)
    V12 = sandwich(bread, U, inter, k)
    V = V1 + V2 - V12
    ev, vec = np.linalg.eigh((V + V.T) / 2)
    info = {"min_eig": float(ev.min()), "psd_fixed": bool(ev.min() < 0)}
    if ev.min() < 0:
        V = vec @ np.diag(np.clip(ev, 0, None)) @ vec.T
    return V, info


def fit_pooled_logit(
    X: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    receiver: np.ndarray,
    names: list[str],
    bio_col: str | None = "has_bio",
) -> dict:
    """Pooled logit, two-way (sender, receiver) clustered SEs, AME of `bio_col` in p.p."""
    t0 = time.time()
    beta, n_iter, conv = _logit_newton(X, y)
    p = expit(X @ beta)
    w = p * (1 - p)
    bread = np.linalg.inv((X * w[:, None]).T @ X)
    U = X * (y - p)[:, None]
    k = X.shape[1]
    V, info = twoway_cov(bread, U, sender, receiver, k)
    V_s = sandwich(bread, U, sender, k)
    V_r = sandwich(bread, U, receiver, k)
    res = {
        "status": "ok" if conv else "not_converged",
        "n_iter": n_iter,
        "names": list(names),
        "coef": beta.tolist(),
        "se": np.sqrt(np.diag(V)).tolist(),
        "se_sender_only": np.sqrt(np.diag(V_s)).tolist(),
        "se_receiver_only": np.sqrt(np.diag(V_r)).tolist(),
        "se_naive": np.sqrt(np.diag(bread)).tolist(),
        "cov": V.tolist(),
        "loglik": float(np.sum(y * np.log(p) + (1 - y) * np.log1p(-p))),
        **info,
    }
    if bio_col is not None and bio_col in names:
        res["ame"] = ame_binary(X, beta, V, names.index(bio_col))
    res["time_s"] = time.time() - t0
    return res


def ame_binary(X: np.ndarray, beta: np.ndarray, V: np.ndarray, j: int) -> dict:
    """Average discrete effect of binary column j (p.p.), delta-method SE with cov V."""
    X1, X0 = X.copy(), X.copy()
    X1[:, j], X0[:, j] = 1.0, 0.0
    p1, p0 = expit(X1 @ beta), expit(X0 @ beta)
    ame = float(np.mean(p1 - p0))
    grad = ((p1 * (1 - p1))[:, None] * X1 - (p0 * (1 - p0))[:, None] * X0).mean(axis=0)
    se = float(np.sqrt(grad @ V @ grad))
    return {
        "ame_pp": 100 * ame,
        "se_pp": 100 * se,
        "lo95_pp": 100 * (ame - 1.959964 * se),
        "hi95_pp": 100 * (ame + 1.959964 * se),
    }


# ----------------------------------------------------------------------------- sender FE logit


def fit_fe_logit(
    X: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    receiver: np.ndarray,
    names: list[str],
    max_iter: int = 200,
    tol: float = 1e-9,
) -> dict:
    """Logit with sender fixed effects (concentrated Newton), SEs clustered by receiver.

    Senders with only 0s or only 1s carry no information and are dropped. The FE are
    profiled out exactly: the beta step uses the Schur complement of the full Hessian and
    scores demeaned within sender (weights p(1-p)), which equals the dummy-variable MLE.
    Columns without within-sender variation (and `const`) are removed.
    """
    t0 = time.time()
    g = pd.factorize(sender)[0]
    G = g.max() + 1
    ys = np.bincount(g, weights=y, minlength=G)
    ns = np.bincount(g, minlength=G)
    informative = (ys > 0) & (ys < ns)
    keep_rows = informative[g]
    X, y, g, receiver = X[keep_rows], y[keep_rows], g[keep_rows], receiver[keep_rows]
    g = pd.factorize(g)[0]
    G = g.max() + 1
    ns = np.bincount(g, minlength=G)
    # remove intercept and columns with no within-sender variation
    means = np.vstack(
        [np.bincount(g, weights=X[:, j], minlength=G) / ns for j in range(X.shape[1])]
    ).T
    Xd = X - means[g]
    # Keep columns in order (bio variable first) while they add within-sender variation that
    # is not a linear combination of already kept columns (e.g. sex_pair levels of one
    # sender sex sum to 1 within a sender and are collinear with the FE).
    order = sorted(range(len(names)), key=lambda j: (not names[j].startswith("has_bio"), j))
    cols: list[int] = []
    for j in order:
        if names[j] == "const":
            continue
        xj = Xd[:, j]
        nrm = np.linalg.norm(xj)
        if nrm < 1e-8:
            continue
        if cols:
            Q = Xd[:, cols]
            coef, *_ = np.linalg.lstsq(Q, xj, rcond=None)
            resid = np.linalg.norm(xj - Q @ coef)
        else:
            resid = nrm
        if resid > 1e-6 * nrm:
            cols.append(j)
    cols.sort()
    X = X[:, cols]
    nm = [names[j] for j in cols]
    k = X.shape[1]

    beta = np.zeros(k)
    ybar = np.bincount(g, weights=y, minlength=G) / ns
    alpha = np.log(ybar / (1 - ybar))
    conv = False
    n_iter = 0
    for _ in range(max_iter):
        n_iter += 1
        # inner: Newton for every alpha_g given beta (vectorised)
        xb = X @ beta
        for _ in range(50):
            p = expit(xb + alpha[g])
            ga = np.bincount(g, weights=y - p, minlength=G)
            ha = np.maximum(np.bincount(g, weights=p * (1 - p), minlength=G), 1e-300)
            da = ga / ha
            alpha += da
            if np.max(np.abs(da)) < 1e-12:
                break
        p = expit(xb + alpha[g])
        w = p * (1 - p)
        wsum = np.bincount(g, weights=w, minlength=G)
        xbar = np.vstack(
            [np.bincount(g, weights=w * X[:, j], minlength=G) / wsum for j in range(k)]
        ).T
        Xt = X - xbar[g]
        grad = X.T @ (y - p)
        H = (Xt * w[:, None]).T @ Xt
        step = np.linalg.solve(H, grad)
        beta += step
        if np.max(np.abs(step)) < tol:
            conv = True
            break
    # final quantities at the optimum
    xb = X @ beta
    p = expit(xb + alpha[g])
    w = p * (1 - p)
    wsum = np.bincount(g, weights=w, minlength=G)
    xbar = np.vstack([np.bincount(g, weights=w * X[:, j], minlength=G) / wsum for j in range(k)]).T
    Xt = X - xbar[g]
    bread = np.linalg.inv((Xt * w[:, None]).T @ Xt)
    U = Xt * (y - p)[:, None]
    V = sandwich(bread, U, receiver, k + G)
    finite = bool(np.all(np.isfinite(beta)) and np.all(np.isfinite(np.diag(V))))
    return {
        "status": ("ok" if conv else "not_converged") if finite else "failed_nonfinite",
        "n_iter": n_iter,
        "names": nm,
        "coef": beta.tolist(),
        "se": np.sqrt(np.diag(V)).tolist(),
        "cov": V.tolist(),
        "se_naive": np.sqrt(np.diag(bread)).tolist(),
        "n_obs_used": int(len(y)),
        "n_senders_used": int(G),
        "n_senders_dropped_all_same": int((~informative).sum()),
        "dropped_cols_no_within_var": [names[j] for j in range(len(names)) if j not in cols],
        "time_s": time.time() - t0,
    }


# ----------------------------------------------------------------------------- helpers


def coef_of(res: dict, name: str) -> tuple[float, float]:
    """(beta, se) of a named coefficient, NaN if absent or the fit failed."""
    if not res or "names" not in res or name not in res["names"]:
        return float("nan"), float("nan")
    i = res["names"].index(name)
    b, se = res["coef"][i], res["se"][i]
    return (float("nan") if b is None else float(b)), (float("nan") if se is None else float(se))
