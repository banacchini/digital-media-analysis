"""Unit tests for the H3a module (synthetic data only, no access to data/)."""

import math

import numpy as np
import pandas as pd
import pytest

from rentfriends.h3a import classify as C
from rentfriends.h3a.data import assign_asof
from rentfriends.h3a.models import fit_fe_logit
from rentfriends.h3a.privacy import suppress_small
from rentfriends.h3a.variables import bio_empty, bio_features, same_city, tag_counts

# ---------------------------------------------------------------- classify

Z90, Z95 = C.Z90, C.Z95


def test_classify_equivalent_zero():
    assert C.classify(0.0, 0.02) == C.PRACTICALLY_ZERO


def test_classify_equivalent_but_significant_positive():
    # 95% CI excludes 0, 90% CI inside the margin
    assert C.classify(0.06, 0.02) == "praktycznie zero (istotnie dodatni)"
    assert C.classify(-0.06, 0.02) == "praktycznie zero (istotnie ujemny)"


def test_classify_confirmed_and_opposite():
    assert C.classify(0.30, 0.05) == C.CONFIRMED
    assert C.classify(-0.30, 0.05) == C.OPPOSITE


def test_classify_inconclusive():
    assert C.classify(0.05, 0.10) == C.INCONCLUSIVE


def test_classify_equivalence_boundary_is_inclusive():
    se = 0.01
    beta = 0.10 - Z90 * se  # upper 90% bound exactly on the margin
    assert C.classify(beta, se).startswith(C.PRACTICALLY_ZERO)
    assert not C.classify(beta + 1e-6, se).startswith(C.PRACTICALLY_ZERO)


def test_classify_significance_boundary():
    se = 0.10
    beta = Z95 * se  # lower 95% bound exactly 0 -> not significant
    assert C.classify(beta, se) == C.INCONCLUSIVE
    assert C.classify(beta + 1e-6, se) == C.CONFIRMED


def test_classify_bad_input():
    assert C.classify(float("nan"), 0.1) == C.NOT_ESTIMATED
    assert C.classify(0.1, 0.0) == C.NOT_ESTIMATED
    assert C.classify(0.1, None) == C.NOT_ESTIMATED


def test_final_label_rules():
    assert C.final_label(C.CONFIRMED, C.CONFIRMED) == C.CONFIRMED
    assert C.final_label(C.CONFIRMED, C.INCONCLUSIVE).startswith(C.SPEC_SENSITIVE)
    out = C.final_label(C.CONFIRMED, C.CONFIRMED, C.INCONCLUSIVE)
    assert C.ESTIMATOR_SENSITIVE in out


def test_mde():
    assert math.isclose(C.mde_or(0.1), math.exp(0.28))


# ---------------------------------------------------------------- bio_empty


def test_bio_empty_definition():
    s = pd.Series([None, "", "   ", "a", " a ", "\n\t"])
    assert bio_empty(s).tolist() == [1, 1, 1, 0, 0, 1]


def test_bio_features_alt10_and_cap():
    s = pd.Series(["123456789", "1234567890", "x" * 250, None])
    f = bio_features(s)
    assert f["bio_empty_alt10"].tolist() == [1, 0, 0, 1]
    assert f["bio_len_cap"].tolist() == [0, 0, 1, 0]
    assert f["has_bio"].tolist() == [1, 1, 1, 0]
    assert f["bio_len"].tolist() == [9, 10, 250, 0]


def test_tag_counts_dedup_after_mapping():
    tm = {"🎓 Student": "student", "student": "student"}
    s = pd.Series(['["🎓 Student", "student", "x"]', "[]"])
    f = tag_counts(s, tm)
    assert f["tag_count_raw"].tolist() == [3, 0]
    assert f["tag_count_receiver"].tolist() == [2, 0]
    assert f["tag_zero"].tolist() == [0, 1]


def test_same_city():
    a = pd.Series(["Wrocław", "Wrocław", "inne", None])
    b = pd.Series(["Wrocław", "Kraków", "inne", "Kraków"])
    assert same_city(a, b).tolist() == ["same", "different", "unknown", "unknown"]


# ---------------------------------------------------------------- as-of rule


@pytest.fixture
def history():
    return pd.DataFrame(
        {
            "user_key": ["u1", "u1", "u1", "u1"],
            "version": [1, 2, 3, 4],
            "day": [10, 10, 20, 30],
        }
    )


def test_asof_rules(history):
    ev = pd.DataFrame(
        {
            "user_key": ["u1", "u1", "u1", "u1", "u1", "u1", "u9"],
            "day": [5, 10, 11, 20, 21, 40, 15],
        }
    )
    out = assign_asof(ev, history, "user_key", users_without_history={"u9"})
    # before first version and on its day -> v1 (first_version)
    assert out["version"].tolist()[:2] == [1, 1]
    assert out["asof_source"].tolist()[:2] == ["first_version", "first_version"]
    # day 11: last version before day 11 = highest version of day 10 -> v2
    assert out["version"].iloc[2] == 2
    # day 20 (change day): version from before the day -> v2, not v3
    assert out["version"].iloc[3] == 2
    assert out["version"].iloc[4] == 3
    assert out["version"].iloc[5] == 4
    assert set(out["asof_source"].iloc[2:6]) == {"prior_version"}
    # no history -> current users row
    assert out["version"].iloc[6] == -1
    assert out["asof_source"].iloc[6] == "users_current"


def test_asof_unknown_user_raises(history):
    ev = pd.DataFrame({"user_key": ["zz"], "day": [3]})
    with pytest.raises(ValueError):
        assign_asof(ev, history, "user_key", users_without_history=set())


# ---------------------------------------------------------------- suppression


def test_suppress_small():
    df = pd.DataFrame({"group": ["a", "b"], "n_users": [4, 5], "rate": [0.1, 0.2]})
    out = suppress_small(df, "n_users", ["rate"])
    assert out["suppressed"].tolist() == [True, False]
    assert np.isnan(out.loc[0, "rate"]) and np.isnan(out.loc[0, "n_users"])
    assert out.loc[1, "rate"] == 0.2 and out.loc[1, "n_users"] == 5
    assert out.loc[0, "group"] == "a"


# ---------------------------------------------------------------- FE logit


def test_fe_logit_matches_dummy_logit():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(0)
    n, G = 3000, 40
    g = rng.integers(0, G, n)
    rec = rng.integers(0, 60, n)
    x = rng.normal(size=(n, 2))
    a = rng.normal(0, 1, G)
    y = rng.binomial(1, 1 / (1 + np.exp(-(a[g] + x @ [0.5, -0.3]))))
    X = np.column_stack([np.ones(n), x])
    res = fit_fe_logit(X, y.astype(float), g, rec, ["const", "x1", "x2"])
    D = pd.get_dummies(pd.Series(g), dtype=float).to_numpy()
    full = sm.Logit(y, np.column_stack([x, D])).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": rec}
    )
    np.testing.assert_allclose(res["coef"], full.params[:2], rtol=1e-6)
    np.testing.assert_allclose(res["se"], full.bse[:2], rtol=1e-6)
