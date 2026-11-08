"""Pre-registered verdict rule for H3a (prompt section 7). Do not change after seeing results."""

from __future__ import annotations

import math

from scipy.stats import norm

Z95 = norm.ppf(0.975)
Z90 = norm.ppf(0.95)

PRACTICALLY_ZERO = "praktycznie zero"
CONFIRMED = "potwierdzony"
OPPOSITE = "efekt przeciwny do hipotezy"
INCONCLUSIVE = "nierozstrzygający"
NOT_ESTIMATED = "brak oszacowania"
SPEC_SENSITIVE = "wrażliwy na specyfikację"
ESTIMATOR_SENSITIVE = "wrażliwy na estymator"


def classify(beta: float, se: float, margin: float = 0.10) -> str:
    """Verdict label for a log-odds coefficient `beta` with standard error `se`.

    Order: equivalence (90% CI inside [-margin, margin], i.e. TOST at alpha = 0.05) first,
    then significance of the 95% CI. Equivalence labels get a suffix when the 95% CI also
    excludes zero.
    """
    if beta is None or se is None or not math.isfinite(beta) or not math.isfinite(se) or se <= 0:
        return NOT_ESTIMATED
    lo90, hi90 = beta - Z90 * se, beta + Z90 * se
    lo95, hi95 = beta - Z95 * se, beta + Z95 * se
    sig_pos = lo95 > 0
    sig_neg = hi95 < 0
    if lo90 >= -margin and hi90 <= margin:
        if sig_pos:
            return f"{PRACTICALLY_ZERO} (istotnie dodatni)"
        if sig_neg:
            return f"{PRACTICALLY_ZERO} (istotnie ujemny)"
        return PRACTICALLY_ZERO
    if sig_pos:
        return CONFIRMED
    if sig_neg:
        return OPPOSITE
    return INCONCLUSIVE


def final_label(label_m1: str, label_m2: str, label_lme4: str | None = None) -> str:
    """Agreement rule: M1 and M2 must agree; lme4 disagreement adds a flag."""
    if label_m1 == NOT_ESTIMATED:
        out = f"{label_m2} (tylko M2: M1 bez oszacowania)"
    elif label_m1 == label_m2:
        out = label_m1
    else:
        out = f"{SPEC_SENSITIVE} (M1: {label_m1}; M2: {label_m2})"
    if label_lme4 is not None and label_lme4 not in (NOT_ESTIMATED, label_m1):
        out = f"{out}; {ESTIMATOR_SENSITIVE} (lme4: {label_lme4})"
    return out


def mde_or(se: float) -> float:
    """Minimal detectable OR at 80% power, two-sided alpha = 0.05: exp(2.80 * SE)."""
    return math.exp(2.80 * se) if se is not None and math.isfinite(se) else float("nan")


def wald_ci(beta: float, se: float) -> dict[str, float]:
    """Log-odds Wald intervals and ORs at 95% and 90%."""
    return {
        "beta": beta,
        "se": se,
        "or": math.exp(beta),
        "or_lo95": math.exp(beta - Z95 * se),
        "or_hi95": math.exp(beta + Z95 * se),
        "or_lo90": math.exp(beta - Z90 * se),
        "or_hi90": math.exp(beta + Z90 * se),
        "p": float(2 * norm.sf(abs(beta / se))) if se > 0 else float("nan"),
    }


def classify_interval(
    beta_lo90: float,
    beta_hi90: float,
    beta_lo95: float,
    beta_hi95: float,
    margin: float = 0.10,
) -> str:
    """Same rule as `classify`, for intervals that are not Wald (e.g. profile likelihood).

    Arguments are log-odds limits of the 90% and 95% intervals.
    """
    vals = (beta_lo90, beta_hi90, beta_lo95, beta_hi95)
    if any(v is None or not math.isfinite(v) for v in vals):
        return NOT_ESTIMATED
    sig_pos, sig_neg = beta_lo95 > 0, beta_hi95 < 0
    if beta_lo90 >= -margin and beta_hi90 <= margin:
        if sig_pos:
            return f"{PRACTICALLY_ZERO} (istotnie dodatni)"
        if sig_neg:
            return f"{PRACTICALLY_ZERO} (istotnie ujemny)"
        return PRACTICALLY_ZERO
    if sig_pos:
        return CONFIRMED
    if sig_neg:
        return OPPOSITE
    return INCONCLUSIVE
