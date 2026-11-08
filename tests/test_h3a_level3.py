"""Unit tests for H3a level 3 helpers (synthetic data only)."""

import math
import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from scipy.stats import chi2, norm

from rentfriends.h3a import classify as C
from rentfriends.h3a import models as M
from rentfriends.h3a import stats3 as S

# ---------------------------------------------------------------- E-value


def test_e_value_known_values():
    # VanderWeele & Ding: RR = 2 -> E = 2 + sqrt(2) = 3.414
    assert S.e_value_rr(2.0) == pytest.approx(2 + math.sqrt(2))
    # protective RR is inverted
    assert S.e_value_rr(0.5) == pytest.approx(S.e_value_rr(2.0))
    assert S.e_value_rr(1.0) == pytest.approx(1.0)


def test_e_value_or_uses_sqrt_and_ci_limit():
    out = S.e_value_or(1.21, 1.10, 1.33)
    assert out["e_point"] == pytest.approx(S.e_value_rr(1.1))
    assert out["e_ci_limit"] == pytest.approx(S.e_value_rr(math.sqrt(1.10)))
    # CI containing 1 -> E-value of the limit is 1
    assert S.e_value_or(1.06, 0.97, 1.16)["e_ci_limit"] == 1.0
    # OR < 1: the upper limit is the one closer to 1
    low = S.e_value_or(0.8, 0.7, 0.9)
    assert low["e_ci_limit"] == pytest.approx(S.e_value_rr(math.sqrt(0.9)))


# ---------------------------------------------------------------- LRT, Wald, profile


def test_lrt_from_two_loglik():
    out = S.lrt(-100.0, -103.0)
    assert out["stat"] == pytest.approx(6.0)
    assert out["p"] == pytest.approx(chi2.sf(6.0, 1))
    assert S.lrt(-100.0, -100.5)["stat"] == pytest.approx(1.0)


def test_wald_chi2():
    out = S.wald_chi2(np.array([1.0, 2.0]), np.diag([1.0, 4.0]))
    assert out["chi2"] == pytest.approx(2.0) and out["df"] == 2
    assert out["p"] == pytest.approx(chi2.sf(2.0, 2))


def test_profile_ci_recovers_wald_for_quadratic():
    b_hat, se = 0.13, 0.05
    grid = np.linspace(b_hat - 4 * se, b_hat + 4 * se, 9)
    ll = -0.5 * ((grid - b_hat) / se) ** 2 - 1234.5
    ci = S.profile_ci(list(grid), list(ll))
    z95, z90 = norm.ppf(0.975), norm.ppf(0.95)
    assert ci["beta_hat_profile"] == pytest.approx(b_hat, abs=1e-3)
    assert ci["lo95"] == pytest.approx(b_hat - z95 * se, abs=2e-3)
    assert ci["hi95"] == pytest.approx(b_hat + z95 * se, abs=2e-3)
    assert ci["lo90"] == pytest.approx(b_hat - z90 * se, abs=2e-3)


def test_profile_ci_nan_when_grid_too_narrow():
    grid = np.linspace(0.12, 0.14, 5)
    ll = -0.5 * ((grid - 0.13) / 0.05) ** 2
    assert math.isnan(S.profile_ci(list(grid), list(ll))["lo95"])


def test_classify_interval_matches_wald():
    b, se = 0.17, 0.05
    args = (b - C.Z90 * se, b + C.Z90 * se, b - C.Z95 * se, b + C.Z95 * se)
    assert C.classify_interval(*args) == C.classify(b, se)
    b, se = 0.01, 0.02
    args = (b - C.Z90 * se, b + C.Z90 * se, b - C.Z95 * se, b + C.Z95 * se)
    assert C.classify_interval(*args) == C.classify(b, se)
    assert C.classify_interval(float("nan"), 0, 0, 0) == C.NOT_ESTIMATED


# ---------------------------------------------------------------- probabilities (A5)


def _toy():
    rng = np.random.default_rng(1)
    n = 400
    x = rng.normal(size=n)
    d = rng.integers(0, 2, n).astype(float)
    X = np.column_stack([np.ones(n), d, x])
    beta = np.array([-1.4, 0.3, 0.2])
    V = np.diag([0.01, 0.004, 0.002])
    return X, beta, V


def test_standardized_probs_matches_manual_computation():
    X, beta, V = _toy()
    out = S.standardized_probs(X, beta, V, 1)
    X0, X1 = X.copy(), X.copy()
    X0[:, 1], X1[:, 1] = 0, 1
    p0, p1 = expit(X0 @ beta).mean(), expit(X1 @ beta).mean()
    assert out["p0"]["pct"] == pytest.approx(100 * p0)
    assert out["p1"]["pct"] == pytest.approx(100 * p1)
    assert out["diff"]["pct"] == pytest.approx(100 * (p1 - p0))
    assert out["per100_p0"] == round(100 * p0, 1)
    # delta method for the difference vs numerical gradient
    eps = 1e-6

    def diff(b):
        return (expit(X1 @ b) - expit(X0 @ b)).mean()

    grad = np.array([(diff(beta + eps * e) - diff(beta - eps * e)) / (2 * eps) for e in np.eye(3)])
    assert out["diff"]["se_pp"] == pytest.approx(100 * math.sqrt(grad @ V @ grad), rel=1e-5)
    assert out["diff"]["lo95"] < out["diff"]["pct"] < out["diff"]["hi95"]


def test_standardized_probs_agree_with_ame():
    X, beta, V = _toy()
    ame = M.ame_binary(X, beta, V, 1)
    out = S.standardized_probs(X, beta, V, 1)
    assert out["diff"]["pct"] == pytest.approx(ame["ame_pp"])
    assert out["diff"]["se_pp"] == pytest.approx(ame["se_pp"], rel=1e-4)


def test_translate_beta_to_pp():
    p0 = np.full(10, 0.2)
    got = S.translate_beta_to_pp(p0, math.log(1.2))
    # baseline odds 0.25, times OR 1.2 = odds 0.30 -> p = 0.30 / 1.30
    assert got == pytest.approx(100 * (0.30 / 1.30 - 0.2))
    assert S.translate_beta_to_pp(p0, 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------- age bins (A2)


def test_age_bin_edges():
    s = pd.Series([-3, 0, 1, 7, 8, 40, np.nan])
    out = S.age_bin(s).tolist()
    assert out[:6] == ["0", "0", "1-7", "1-7", "≥ 8", "≥ 8"]
    assert pd.isna(out[6])


# ---------------------------------------------------------------- design (A2, A3)


def _frame(n=300, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "y_right": rng.integers(0, 2, n),
            "has_bio": rng.integers(0, 2, n),
            "sex_pair": rng.choice(["F→F", "F→M", "M→F", "M→M"], n),
            "age_band_diff": rng.integers(-1, 2, n),
            "same_band": rng.integers(0, 2, n).astype(float),
            "same_city": rng.choice(["same", "diff"], n),
            "profile_completeness": rng.random(n),
            "tag_count_receiver": rng.integers(0, 9, n).astype(float),
            "tag_zero": rng.integers(0, 2, n),
            "tag_cap": rng.integers(0, 2, n),
            "asof_prior": rng.integers(0, 2, n),
        }
    )


def test_control_sets_are_nested():
    t = _frame()
    cols = {
        cs: list(M.build_design(t, M.Spec(control_set=cs))[0].columns)
        for cs in ("none", "demog", "demog_completeness", "full")
    }
    assert cols["none"] == ["const", "has_bio"]
    assert set(cols["none"]) < set(cols["demog"]) < set(cols["demog_completeness"])
    assert set(cols["demog_completeness"]) < set(cols["full"])
    assert "profile_completeness" not in cols["demog"]
    assert "tag_count_receiver" not in cols["demog_completeness"]
    # default spec equals the "full" set (unchanged main specification)
    assert list(M.build_design(t, M.Spec())[0].columns) == cols["full"]


def test_interaction_columns():
    t = _frame()
    X, _ = M.build_design(t, M.Spec(interact_cols=("asof_prior",)))
    assert {"asof_prior", "has_bio:asof_prior"} <= set(X.columns)
    assert np.allclose(X["has_bio:asof_prior"], t["has_bio"] * t["asof_prior"])


def test_fe_logit_returns_cov():
    t = _frame(600)
    t["s"] = np.repeat(np.arange(60), 10)
    X, _ = M.build_design(t, M.Spec(control_set="none"))
    out = M.fit_fe_logit(
        X.to_numpy(float),
        t["y_right"].to_numpy(float),
        t["s"].to_numpy(),
        t["s"].to_numpy(),
        list(X.columns),
    )
    k = len(out["names"])
    assert np.array(out["cov"]).shape == (k, k)
    assert np.sqrt(np.diag(out["cov"])) == pytest.approx(out["se"])


# ---------------------------------------------------------------- lme4 via temporary CSV (B2)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_lme4_fit_recovers_known_beta(tmp_path, monkeypatch):
    from rentfriends.h3a.analysis import lme4_fit

    r = subprocess.run(["Rscript", "-e", "library(lme4)"], capture_output=True)
    if r.returncode:
        pytest.skip("lme4 not installed")
    rng = np.random.default_rng(7)
    n_s, n_r, n = 150, 150, 12000
    s = rng.integers(0, n_s, n)
    rc = rng.integers(0, n_r, n)
    a, b = rng.normal(0, 0.7, n_s), rng.normal(0, 0.5, n_r)
    bio = rng.integers(0, 2, n).astype(float)
    z = rng.normal(size=n)
    eta = -1.0 + 0.5 * bio + 0.2 * z + a[s] + b[rc]
    y = (rng.random(n) < expit(eta)).astype(float)
    X = np.column_stack([np.ones(n), bio, z])
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    out = lme4_fit(X, y, s, rc, ["const", "has_bio", "z"], timeout_s=300, with_lrt=True)
    assert out["status"] == "ok"
    b_hat, se = M.coef_of(out, "has_bio")
    assert abs(b_hat - 0.5) < 4 * se
    assert 0.2 < out["var_sender"] < 0.9 and 0.1 < out["var_receiver"] < 0.6
    assert out["lrt_p"] < 0.01 and out["lrt_stat"] > 0
    assert not list(tmp_path.iterdir()), "temporary directory must be removed"


# ---------------------------------------------------------------- numbers JSON (Polish format)


def test_fmt_pl_decimal_comma_and_nbsp():
    from rentfriends.h3a.export3 import NBSP, fmt_pl

    assert fmt_pl(1.234, 2) == "1,23"
    assert fmt_pl(93717, 0) == f"93{NBSP}717"
    assert fmt_pl(-1.2, 1) == "−1,2"
    assert fmt_pl(float("nan")) == "–"


def test_add_pl_adds_sibling_keys():
    from rentfriends.h3a.export3 import NBSP, add_pl

    out = add_pl(
        {"n_obs": 93717, "or": 1.1301, "p": 0.0002, "pct": 14.366, "nested": {"lo95": -1.19}}
    )
    assert out["n_obs_pl"] == f"93{NBSP}717"
    assert out["or_pl"] == "1,13"
    assert out["p_pl"] == "<0,001"
    assert out["pct_pl"] == "14,4"
    assert out["nested"]["lo95_pl"] == "−1,2"
    assert out["or"] == 1.1301  # raw value kept


def test_classify_interval_cases():
    m = 0.10
    # CI wholly inside the margin, 95% CI excludes 0 -> practically zero (significant positive)
    assert C.classify_interval(0.02, 0.08, 0.015, 0.085, m).startswith(C.PRACTICALLY_ZERO)
    assert C.classify_interval(-0.30, -0.10, -0.35, -0.05, m) == C.OPPOSITE
    assert C.classify_interval(-0.05, 0.30, -0.10, 0.35, m) == C.INCONCLUSIVE
    assert C.classify_interval(0.04, 0.30, 0.03, 0.35, m) == C.CONFIRMED
