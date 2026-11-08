"""Unit tests for H1 hypothesis analysis module."""

import numpy as np
import pandas as pd

from rentfriends.h1 import (
    LEGACY_SPEC,
    SAME_SEX_SPEC,
    H1Spec,
    cluster_bootstrap_rate_table,
    control_frame,
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
            "age_band_diff": rng.integers(-2, 3, size=n).astype(float),
            "age_band_diff_abs": rng.integers(0, 3, size=n).astype(float),
            "age_band_sender": rng.choice(["18-20", "21-23", "24-26"], size=n),
            "same_sex": rng.integers(0, 2, size=n).astype(float),
            "sex_pair": rng.choice(["F_F", "F_M", "M_F", "M_M", "F_O"], size=n),
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


def test_sex_pair_control_is_default_and_has_reference_level():
    """Z2: the main specification controls for the ordered sex pair, not for same_sex."""
    df = _make_dummy_h1_df(400)
    ctrl = control_frame(df, H1Spec())
    sex_cols = [c for c in ctrl.columns if c.startswith("sex_")]
    assert "sex_F_F" not in sex_cols  # reference level
    assert {"sex_F_M", "sex_M_F", "sex_M_M", "sex_F_O"} == set(sex_cols)
    assert "same_sex" not in ctrl.columns


def test_legacy_spec_reproduces_old_variable_counts():
    """spec_old keeps the pre-audit design: same_sex inside the age block, only city controls."""
    df = _make_dummy_h1_df(400)
    res = fit_h1_logit_models(df, LEGACY_SPEC)
    n_vars = res["summary"].set_index("model")["n_vars"]
    assert res["control_names"] == ["city_same", "city_diff"]
    assert n_vars["age"] == 5  # old "demog"
    assert n_vars["lifestyle"] == 5
    assert n_vars["age_interests"] == 8
    assert n_vars["full"] == 11


def test_same_sex_spec_is_a_sensitivity_variant():
    df = _make_dummy_h1_df(400)
    res = fit_h1_logit_models(df, SAME_SEX_SPEC)
    assert "same_sex" in res["control_names"]


def test_main_age_spec_has_abs_and_signed_difference_without_square():
    """Z3: same_band + |diff| + signed diff; the square is only a sensitivity variant."""
    spec = H1Spec()
    assert spec.age_cols == ("same_band", "age_band_diff_abs", "age_band_diff")
    df = _make_dummy_h1_df(300)
    sq = fit_h1_logit_models(df, H1Spec(name="sq", age_sq=True))
    base = fit_h1_logit_models(df)
    n_base = base["summary"].set_index("model")["n_vars"]["age"]
    assert sq["summary"].set_index("model")["n_vars"]["age"] == n_base + 1


def test_sender_band_fixed_effects_add_controls():
    df = _make_dummy_h1_df(300)
    ctrl = control_frame(df, H1Spec(name="fe", sender_band_fe=True))
    fe_cols = [c for c in ctrl.columns if c.startswith("sband_")]
    assert set(fe_cols) == {"sband_21-23", "sband_24-26"}  # 18-20 is the reference
