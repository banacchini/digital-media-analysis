"""Pure statistical helpers for H3a level 3 (diagnostics, SE ladder). No I/O."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq
from scipy.special import expit, logit
from scipy.stats import chi2

Z95 = 1.959964

AGE_BIN_LABELS = ["0", "1-7", "≥ 8"]


def age_bin(days: pd.Series) -> pd.Series:
    """Account/profile age bins fixed in advance: 0 (also swipes dated before the first
    recorded version), 1-7, >= 8 days. NaN stays NaN."""
    d = days.astype(float)
    out = pd.Series(pd.NA, index=days.index, dtype="object")
    out[d <= 0] = AGE_BIN_LABELS[0]
    out[(d >= 1) & (d <= 7)] = AGE_BIN_LABELS[1]
    out[d >= 8] = AGE_BIN_LABELS[2]
    return out


# ----------------------------------------------------------------------------- E-value


def e_value_rr(rr: float) -> float:
    """VanderWeele-Ding E-value for a risk ratio (RR < 1 is inverted first)."""
    if not math.isfinite(rr) or rr <= 0:
        return float("nan")
    rr = 1 / rr if rr < 1 else rr
    return rr + math.sqrt(rr * (rr - 1))


def e_value_or(odds_ratio: float, lo: float, hi: float) -> dict:
    """E-value for a common outcome (baseline ~20%): RR is approximated by sqrt(OR).

    Returns the E-value of the point estimate and of the CI limit closer to 1
    (1.0 when the CI contains 1).
    """
    point = e_value_rr(math.sqrt(odds_ratio))
    if lo <= 1 <= hi:
        bound = 1.0
    else:
        limit = lo if odds_ratio >= 1 else hi
        bound = e_value_rr(math.sqrt(limit))
    return {"e_point": point, "e_ci_limit": bound}


# ----------------------------------------------------------------------------- Wald, LRT


def wald_chi2(beta: np.ndarray, V: np.ndarray) -> dict:
    """Wald test that all of `beta` are zero, with covariance `V`."""
    beta = np.asarray(beta, float)
    if beta.size == 0:
        return {"chi2": float("nan"), "df": 0, "p": float("nan")}
    w = float(beta @ np.linalg.solve(np.atleast_2d(V), beta))
    return {"chi2": w, "df": int(beta.size), "p": float(chi2.sf(w, beta.size))}


def lrt(ll_full: float, ll_null: float, df: int = 1) -> dict:
    """Likelihood-ratio test from two log-likelihoods."""
    stat = 2 * (ll_full - ll_null)
    return {"stat": stat, "df": df, "p": float(chi2.sf(max(stat, 0.0), df))}


def profile_ci(grid: list[float], loglik: list[float], levels=(0.95, 0.90)) -> dict:
    """Profile-likelihood CIs from log-likelihood values on a grid of fixed coefficients.

    A cubic spline through the grid is searched on both sides of its maximum for the point
    where 2*(l_max - l) equals the chi-square(1) quantile. Returns NaN on a side where the grid
    does not reach the threshold.
    """
    g, ll = np.asarray(grid, float), np.asarray(loglik, float)
    order = np.argsort(g)
    g, ll = g[order], ll[order]
    cs = CubicSpline(g, ll)
    fine = np.linspace(g[0], g[-1], 4001)
    vals = cs(fine)
    i_max = int(np.argmax(vals))
    b_hat, l_max = float(fine[i_max]), float(vals[i_max])
    out: dict = {"beta_hat_profile": b_hat, "ll_max_profile": l_max}
    for lev in levels:
        thr = float(chi2.ppf(lev, 1))

        def f(b, thr=thr):
            return 2 * (l_max - float(cs(b))) - thr

        lo = hi = float("nan")
        if f(g[0]) > 0:
            lo = brentq(f, g[0], b_hat)
        if f(g[-1]) > 0:
            hi = brentq(f, b_hat, g[-1])
        out[f"lo{int(lev * 100)}"], out[f"hi{int(lev * 100)}"] = lo, hi
    return out


# ----------------------------------------------------------------------------- probabilities


def standardized_probs(X: np.ndarray, beta: np.ndarray, V: np.ndarray, j: int) -> dict:
    """Average predicted P(y = 1) with binary column j set to 0 and to 1 for all rows.

    Returns percentages with delta-method SEs (covariance `V`) for each level and for their
    difference (percentage points).
    """
    X1, X0 = X.copy(), X.copy()
    X1[:, j], X0[:, j] = 1.0, 0.0
    p1, p0 = expit(X1 @ beta), expit(X0 @ beta)
    g1 = ((p1 * (1 - p1))[:, None] * X1).mean(axis=0)
    g0 = ((p0 * (1 - p0))[:, None] * X0).mean(axis=0)
    out = {}
    for name, p, g in (("p0", p0, g0), ("p1", p1, g1), ("diff", p1 - p0, g1 - g0)):
        est = float(p.mean())
        se = float(np.sqrt(g @ V @ g))
        out[name] = {
            "pct": 100 * est,
            "se_pp": 100 * se,
            "lo95": 100 * (est - Z95 * se),
            "hi95": 100 * (est + Z95 * se),
        }
    out["per100_p0"] = round(out["p0"]["pct"], 1)
    out["per100_p1"] = round(out["p1"]["pct"], 1)
    out["n"] = int(X.shape[0])
    return out


def translate_beta_to_pp(p0: np.ndarray, beta: float) -> float:
    """Effect in p.p. of adding `beta` log-odds to baseline risks `p0` (mean over rows).

    Used to express the sender-FE logit (M3) on the same scale as the AME of the pooled logit:
    the FE are not identified as a population-average probability, so the pooled baseline risks
    are used as the reference distribution.
    """
    p0 = np.clip(np.asarray(p0, float), 1e-12, 1 - 1e-12)
    return float(100 * np.mean(expit(logit(p0) + beta) - p0))
