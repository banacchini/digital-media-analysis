"""Unit tests for H1 hypothesis analysis module."""

import numpy as np
import pandas as pd

from rentfriends.h1 import (
    cluster_bootstrap_rate_table,
    fit_h1_logit_models,
    grouped_cv_h1,
    wilson_interval,
)


def _make_dummy_h1_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    senders = [f"u{i}" for i in rng.integers(1, 20, size=n)]
    receivers = [f"u{i}" for i in rng.integers(21, 50, size=n)]
    return pd.DataFrame(
        {
            "user_key": senders,
            "target_user_key": receivers,
            "y_right": rng.integers(0, 2, size=n),
            "same_band": rng.integers(0, 2, size=n).astype(float),
            "age_band_diff": rng.normal(0, 1, size=n),
            "same_sex": rng.integers(0, 2, size=n).astype(float),
            "interests_jaccard": rng.uniform(0, 1, size=n),
            "interests_shared_n": rng.integers(0, 5, size=n),
            "interests_count_diff_abs": rng.integers(0, 4, size=n),
            "lifestyle_agree_ratio": rng.uniform(0, 1, size=n),
            "lifestyle_tag_conflict": rng.integers(0, 2, size=n),
            "lifestyle_shared_tags_n": rng.integers(0, 3, size=n),
            "city_same": rng.integers(0, 2, size=n).astype(float),
            "city_diff": rng.integers(0, 2, size=n).astype(float),
        }
    )


def test_wilson_interval():
    lo, hi = wilson_interval(20, 100)
    assert 0.1 < lo < 0.2
    assert 0.2 < hi < 0.3


def test_cluster_bootstrap_rate_table():
    df = _make_dummy_h1_df(100)
    res = cluster_bootstrap_rate_table(df, "same_band", n_boot=50, seed=42)
    assert len(res) == 2
    assert "ci_low_boot" in res.columns


def test_fit_h1_logit_models():
    df = _make_dummy_h1_df(300)
    res = fit_h1_logit_models(df)
    assert "models" in res
    assert "delta_lifestyle_over_interests_ll" in res
    assert set(res["models"]) == {
        "null",
        "controls",
        "age",
        "interests",
        "lifestyle",
        "age_interests",
        "age_lifestyle",
        "interests_lifestyle",
        "full",
    }


def test_all_models_share_identical_controls():
    """Z1: every non-null model contains the same control columns and the same sample."""
    df = _make_dummy_h1_df(400)
    res = fit_h1_logit_models(df)
    controls = set(res["control_names"])
    assert controls  # at least city + sex control
    for name, fit in res["models"].items():
        if name == "null":
            continue
        assert controls <= set(fit.params.index), name
    assert len({int(fit.nobs) for fit in res["models"].values()}) == 1


def test_block_models_add_only_their_block():
    df = _make_dummy_h1_df(400)
    res = fit_h1_logit_models(df)
    n_ctrl = len(res["control_names"])
    n_vars = res["summary"].set_index("model")["n_vars"]
    assert n_vars["controls"] == n_ctrl
    assert n_vars["lifestyle"] == n_ctrl + 3
    assert n_vars["age_interests"] == n_vars["age"] + n_vars["interests"] - n_ctrl
    assert n_vars["full"] == n_ctrl + (n_vars["age"] - n_ctrl) + 3 + 3


def test_grouped_cv_h1():
    df = _make_dummy_h1_df(300)
    cv = grouped_cv_h1(df, n_splits=3, seed=42)
    assert len(cv) == 3 * 9
    assert "logloss" in cv.columns
    assert "auc" in cv.columns
