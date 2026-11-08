"""Unit tests for the H1 audit helpers (age direction, block increments, bootstrap, ...)."""

import numpy as np
import pandas as pd

from conftest import make_dummy_h1_df
from rentfriends.dataset_h1 import idf_weights
from rentfriends.h1_audit import (
    age_direction_check,
    block_increment_table,
    block_increments_from_fit,
    bootstrap_model_loglik,
    combine_cluster_cis,
    field_dummies,
    fit_logit_fast,
    holm_adjust,
    interests_permutation_baseline,
    oof_predictions,
    paired_cv_differences,
    per_field_analysis,
    permute_within_strata,
    sample_funnel,
    summarise_block_differences,
)


def _make_age_df(n_senders: int = 150, per_sender: int = 60, seed: int = 0) -> pd.DataFrame:
    """Younger-by-one-band receivers get a higher right-swipe rate than the same band."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_senders):
        band = int(rng.integers(0, 3))  # sender band index 0..2
        for _ in range(per_sender):
            diff = int(rng.integers(-band, 3))
            p = 0.15 + (0.12 if diff == -1 else 0.0) - (0.06 if diff >= 1 else 0.0)
            rows.append(
                {
                    "user_key": f"s{u}",
                    "target_user_key": f"r{int(rng.integers(0, 80))}",
                    "age_band_sender": ["18-20", "21-23", "24-26"][band],
                    "age_band_diff": float(diff),
                    "y_right": int(rng.random() < p),
                }
            )
    return pd.DataFrame(rows)


def test_age_direction_detects_younger_receiver_advantage():
    df = _make_age_df()
    res = age_direction_check(df, n_boot=100, seed=1)
    pooled = res["pooled"].set_index("term")
    assert pooled.loc["younger_by_1", "or"] > 1.3
    assert pooled.loc["younger_by_1", "ci_low"] > 1.0
    assert pooled.loc["older_by_1", "or"] < 1.0


def test_age_direction_contrast_is_only_for_senders_who_can_have_younger_targets():
    df = _make_age_df()
    res = age_direction_check(df, n_boot=100, seed=1)
    contrast = res["contrast"]
    assert "18-20" not in set(contrast["age_band_sender"])  # diff=-1 impossible there
    assert (contrast["diff_younger_minus_same"] > 0).all()


def test_age_direction_suppresses_small_cells():
    df = _make_age_df(n_senders=150, per_sender=60)
    # make one rare cell: only 2 distinct senders have diff == -2
    mask = df["age_band_diff"] == -2
    keep_senders = df.loc[mask, "user_key"].unique()[:2]
    df = df[~mask | df["user_key"].isin(keep_senders)]
    res = age_direction_check(df, n_boot=50, seed=1, min_users=5)
    cells = res["cells"]
    rare = cells[cells["age_band_diff"] == -2]
    assert rare["rate"].isna().all()
    assert (rare["n_users"] < 5).all()


def test_block_increment_table_matches_hand_computation():
    """Z4: first / last / mean-over-6-orderings increments and their efficiency property."""
    ll = {
        "controls": 0.0,
        "age": 10.0,
        "interests": 4.0,
        "lifestyle": 2.0,
        "age_interests": 12.0,
        "age_lifestyle": 11.0,
        "interests_lifestyle": 7.0,
        "full": 14.0,
    }
    k = {"age": 3, "interests": 3, "lifestyle": 4}
    tbl = block_increment_table(ll, k).set_index("block")
    assert tbl.loc["age", "dll_first"] == 10.0
    assert tbl.loc["age", "dll_last"] == 7.0
    assert np.isclose(tbl.loc["age", "dll_mean"], 8.5)
    assert np.isclose(tbl.loc["interests", "dll_mean"], 3.5)
    assert np.isclose(tbl.loc["lifestyle", "dll_mean"], 2.0)
    # efficiency: mean increments of the three blocks add up to the total gain
    singles = tbl.loc[["age", "interests", "lifestyle"], "dll_mean"].sum()
    assert np.isclose(singles, 14.0)
    # per-df and AIC (-2*dLL + 2*df)
    assert np.isclose(tbl.loc["lifestyle", "dll_last_per_df"], 2.0 / 4)
    assert np.isclose(tbl.loc["lifestyle", "daic_last"], -2 * 2.0 + 2 * 4)
    # composite row used by the card's criterion: lifestyle vs age+interests
    comp = tbl.loc["age+interests"]
    assert comp["df"] == 6
    assert comp["dll_first"] == 12.0
    assert comp["dll_last"] == 14.0 - 2.0
    assert np.isclose(comp["dll_mean"], (12.0 + 12.0) / 2)


def test_block_increments_from_fit_uses_model_loglik_and_block_df():
    from rentfriends.h1 import fit_h1_logit_models

    res = fit_h1_logit_models(make_dummy_h1_df(400))
    tbl = block_increments_from_fit(res).set_index("block")
    assert tbl.loc["lifestyle", "df"] == 3
    total = res["models"]["full"].llf - res["models"]["controls"].llf
    assert np.isclose(tbl.loc[["age", "interests", "lifestyle"], "dll_mean"].sum(), total)


def _synthetic_effect_df(effect: str, n: int = 6000, seed: int = 3) -> pd.DataFrame:
    """Strong effect in exactly one block; the other blocks are noise."""
    rng = np.random.default_rng(seed)
    senders = rng.integers(0, 120, size=n)
    receivers = rng.integers(0, 120, size=n)
    city = rng.integers(0, 3, size=n)  # 0 same, 1 different, 2 unknown
    df = pd.DataFrame(
        {
            "user_key": [f"s{i}" for i in senders],
            "target_user_key": [f"r{i}" for i in receivers],
            "same_band": rng.integers(0, 2, size=n).astype(float),
            "age_band_diff_abs": rng.integers(0, 3, size=n).astype(float),
            "age_band_diff": rng.integers(-2, 3, size=n).astype(float),
            "same_sex": rng.integers(0, 2, size=n).astype(float),
            "sex_pair": rng.choice(["F_F", "F_M", "M_F", "M_M"], size=n),
            "interests_jaccard": rng.uniform(0, 1, size=n),
            "interests_shared_n": rng.integers(0, 5, size=n),
            "interests_count_diff_abs": rng.integers(0, 4, size=n),
            "lifestyle_agree_ratio": rng.uniform(0, 1, size=n),
            "lifestyle_tag_conflict": rng.integers(0, 2, size=n),
            "lifestyle_shared_tags_n": rng.integers(0, 3, size=n),
            "city_same": (city == 0).astype(float),
            "city_diff": (city == 1).astype(float),
        }
    )
    logit = -1.0
    if effect == "lifestyle":
        logit = logit + 2.5 * (df["lifestyle_agree_ratio"] - 0.5)
    else:
        logit = logit - 0.9 * df["age_band_diff_abs"]
    df["y_right"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


def test_fit_logit_fast_matches_statsmodels_and_row_duplication():
    import statsmodels.api as sm

    rng = np.random.default_rng(0)
    X = sm.add_constant(rng.normal(size=(500, 3)))
    y = (rng.random(500) < 1 / (1 + np.exp(-(X @ [0.3, 0.8, -0.5, 0.0])))).astype(float)
    beta, ll = fit_logit_fast(X, y)
    ref = sm.Logit(y, X).fit(disp=0)
    assert np.allclose(beta, ref.params, atol=1e-6)
    assert np.isclose(ll, ref.llf, atol=1e-6)
    # integer weights are equivalent to duplicating rows
    w = rng.integers(0, 3, size=500).astype(float)
    beta_w, ll_w = fit_logit_fast(X, y, w)
    rows = np.repeat(np.arange(500), w.astype(int))
    ref_w = sm.Logit(y[rows], X[rows]).fit(disp=0)
    assert np.allclose(beta_w, ref_w.params, atol=1e-6)
    assert np.isclose(ll_w, ref_w.llf, atol=1e-6)


def test_bootstrap_loglik_reproducible_and_observed_matches_fit():
    from rentfriends.h1 import fit_h1_logit_models

    df = _synthetic_effect_df("lifestyle", n=2000)
    obs, boot = bootstrap_model_loglik(df, cluster_col="user_key", n_boot=8, seed=5)
    res = fit_h1_logit_models(df)
    for name in obs.index:
        assert np.isclose(obs[name], res["models"][name].llf, atol=1e-5)
    assert boot.shape == (8, 8)
    _, boot2 = bootstrap_model_loglik(df, cluster_col="user_key", n_boot=8, seed=5)
    assert np.allclose(boot.to_numpy(), boot2.to_numpy())


def test_difference_ci_separates_lifestyle_effect_from_age_effect():
    life = _synthetic_effect_df("lifestyle")
    obs, boot = bootstrap_model_loglik(life, cluster_col="user_key", n_boot=60, seed=1)
    tbl = summarise_block_differences(obs, boot, block_df=_SYN_DF).set_index(
        ["definition", "contrast"]
    )
    row = tbl.loc[("last", "lifestyle - age+interests")]
    assert row["estimate"] > 0 and row["ci_low"] > 0

    age = _synthetic_effect_df("age")
    obs, boot = bootstrap_model_loglik(age, cluster_col="user_key", n_boot=60, seed=1)
    tbl = summarise_block_differences(obs, boot, block_df=_SYN_DF).set_index(
        ["definition", "contrast"]
    )
    row = tbl.loc[("last", "lifestyle - age+interests")]
    assert row["estimate"] < 0 and row["ci_high"] < 0
    assert {"first", "last", "mean"} == {k[0] for k in tbl.index}
    assert {"lifestyle - age+interests", "lifestyle - interests", "lifestyle - age"} == {
        k[1] for k in tbl.index
    }


_SYN_DF = {"age": 3, "interests": 3, "lifestyle": 3}


def test_combine_cluster_cis_picks_the_wider_interval():
    cols = ["definition", "contrast", "estimate", "ci_low", "ci_high", "boot_se", "share_positive"]
    by_sender = pd.DataFrame([["last", "c", 1.0, 0.5, 1.5, 0.25, 1.0]], columns=cols)
    by_receiver = pd.DataFrame([["last", "c", 1.0, -0.5, 2.5, 0.75, 0.9]], columns=cols)
    out = combine_cluster_cis(by_sender, by_receiver).iloc[0]
    assert out["ci_low_sender"] == 0.5 and out["ci_high_receiver"] == 2.5
    assert out["ci_low_conservative"] == -0.5 and out["ci_high_conservative"] == 2.5
    assert out["wider_is"] == "receiver"
    assert bool(out["excludes_zero_conservative"]) is False


def test_oof_predictions_never_train_on_the_senders_they_predict():
    df = _synthetic_effect_df("lifestyle", n=2000)
    oof = oof_predictions(df, n_splits=4, seed=2)
    assert {"y", "sender", "fold"} <= set(oof.columns)
    assert {"controls", "age", "interests", "lifestyle", "full"} <= set(oof.columns)
    assert oof.groupby("sender")["fold"].nunique().max() == 1  # each sender in exactly one fold
    assert oof["full"].between(0, 1).all()


def test_paired_cv_differences_sign_matches_the_true_effect():
    life = oof_predictions(_synthetic_effect_df("lifestyle"), n_splits=5, seed=2)
    tbl = paired_cv_differences(life, n_boot=40, seed=1).set_index(
        ["metric", "definition", "contrast"]
    )
    for metric in ("logloss", "auc", "auc_pr"):
        row = tbl.loc[(metric, "last", "lifestyle - age+interests")]
        assert row["estimate"] > 0, metric  # positive = lifestyle improves more
    assert tbl.loc[("logloss", "last", "lifestyle - age+interests"), "ci_low"] > 0

    age = oof_predictions(_synthetic_effect_df("age"), n_splits=5, seed=2)
    tbl = paired_cv_differences(age, n_boot=40, seed=1).set_index(
        ["metric", "definition", "contrast"]
    )
    row = tbl.loc[("auc", "last", "lifestyle - age+interests")]
    assert row["estimate"] < 0 and row["ci_high"] < 0


def _interest_df(signal: bool, n: int = 4000, seed: int = 11) -> pd.DataFrame:
    """Sender/receiver hobby sets; with `signal`, right swipes always share one tag."""
    rng = np.random.default_rng(seed)
    vocab = [f"t{i}" for i in range(30)]
    rows = []
    for _ in range(n):
        s = set(rng.choice(vocab, size=int(rng.integers(2, 6)), replace=False))
        r = set(rng.choice(vocab, size=int(rng.integers(2, 6)), replace=False))
        y = int(rng.random() < 0.3)
        if signal and y == 1:
            r = (r - s) | {sorted(s)[0]}
        if signal and y == 0:
            r = r - s
            if not r:
                r = {"t_other"}
        rows.append(
            {
                "user_key": f"s{int(rng.integers(0, 150))}",
                "target_user_key": f"r{int(rng.integers(0, 150))}",
                "y_right": y,
                "interests_set_sender": sorted(s),
                "interests_set_receiver": sorted(r),
            }
        )
    return pd.DataFrame(rows)


def test_permute_within_strata_keeps_tag_counts():
    rng = np.random.default_rng(0)
    counts = np.array([2, 3, 3, 2, 5, 3, 2, 5, 5, 2])
    perm = permute_within_strata(counts, rng)
    assert sorted(perm) == list(range(len(counts)))  # a true permutation
    assert (counts[perm] == counts).all()  # receiver tag count is preserved per swipe


def test_interest_permutation_baseline_detects_overlap_beyond_chance():
    res = interests_permutation_baseline(_interest_df(signal=True), n_perm=60, seed=1)
    tbl = res["summary"].set_index("group")
    assert tbl.loc["right", "observed"] > tbl.loc["right", "perm_hi"]
    assert tbl.loc["left", "observed"] < tbl.loc["left", "perm_lo"]
    assert tbl.loc["right_minus_left", "p_two_sided"] < 0.05


def test_interest_permutation_baseline_is_quiet_without_signal():
    res = interests_permutation_baseline(_interest_df(signal=False), n_perm=60, seed=1)
    tbl = res["summary"].set_index("group")
    # with no signal the observed gap is a typical draw from the permutation distribution
    diff = tbl.loc["right_minus_left"]
    assert abs(diff["observed"] - diff["perm_mean"]) < 3 * res["perm_diff"].std()
    right = tbl.loc["right"]
    assert right["perm_lo"] <= right["observed"] <= right["perm_hi"]


def test_interest_permutation_baseline_supports_idf_weights():
    df = _interest_df(signal=True, n=1500)
    docs = list(df["interests_set_receiver"])
    weights = idf_weights(docs)
    res = interests_permutation_baseline(df, n_perm=20, seed=1, weights=weights)
    assert res["summary"].set_index("group").loc["right", "observed"] > 0


FIELDS = [
    "daily_routine",
    "lifestyle",
    "work_from_home",
    "cleanliness",
    "noise_level",
    "smoking",
    "alcohol",
]


def _field_df(n: int = 12000, seed: int = 4) -> pd.DataFrame:
    """Only `smoking` matters: non-smoker -> user is rejected, user -> non-smoker is not."""
    rng = np.random.default_rng(seed)
    df = _synthetic_effect_df("lifestyle", n=n, seed=seed).drop(columns=["y_right"])
    for f in FIELDS:
        df[f"lsf_{f}"] = rng.choice(
            ["agree", "disagree", "one_missing", "both_missing"], size=n, p=[0.3, 0.3, 0.3, 0.1]
        )
    df["smoking_direction"] = rng.choice(
        ["agree", "nonsmoker_to_user", "user_to_nonsmoker", "one_missing", "both_missing"],
        size=n,
        p=[0.3, 0.2, 0.2, 0.2, 0.1],
    )
    logit = -1.2 - 1.2 * (df["smoking_direction"] == "nonsmoker_to_user")
    df["y_right"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


def test_holm_adjust_matches_hand_computation():
    adj = holm_adjust(np.array([0.01, 0.04, 0.03]))
    # sorted p: .01*3, .03*2, .04*1 -> .03, .06, .06 (monotone)
    assert np.allclose(adj, [0.03, 0.06, 0.06])


def test_per_field_analysis_finds_the_one_informative_field_with_holm():
    df = _field_df()
    # make the smoking *status* informative too (it is derived from the same direction)
    df["lsf_smoking"] = np.where(
        df["smoking_direction"].isin(["nonsmoker_to_user", "user_to_nonsmoker"]),
        "disagree",
        np.where(df["smoking_direction"] == "agree", "agree", df["smoking_direction"]),
    )
    res = per_field_analysis(df)
    tbl = res["fields"].set_index("field")
    assert set(tbl.index) == set(FIELDS)
    assert tbl.loc["smoking", "p_holm"] < 0.01
    assert (tbl.drop(index="smoking")["p_holm"] > 0.05).all()
    assert (tbl["p_holm"] >= tbl["p_raw"] - 1e-12).all()
    assert tbl.loc["smoking", "dll_last"] > tbl.drop(index="smoking")["dll_last"].max()
    # possible default-value fields are flagged (P6)
    assert bool(tbl.loc["cleanliness", "possible_default"]) and not bool(
        tbl.loc["smoking", "possible_default"]
    )


def test_per_field_analysis_smoking_direction_is_asymmetric():
    res = per_field_analysis(_field_df())
    sm_tbl = res["smoking_direction"].set_index("level")
    assert sm_tbl.loc["nonsmoker_to_user", "or"] < 0.5
    assert 0.8 < sm_tbl.loc["user_to_nonsmoker", "or"] < 1.25
    assert res["smoking_asymmetry_p"] < 0.001


def test_sparse_field_levels_are_merged_into_one_missing():
    df = _field_df()
    status = df["lsf_cleanliness"].replace("both_missing", "agree")
    status.iloc[:3] = "both_missing"  # only 3 rows: far below min_n
    n_one = int((status == "one_missing").sum())
    d = field_dummies(status, "cleanliness", min_n=50)
    assert not any(c.endswith("both_missing") for c in d.columns)
    assert d["cleanliness_one_missing"].sum() == n_one + 3


def test_lifestyle_agree_groups_have_explicit_missing_category_and_no_zero_fill():
    from rentfriends.h1 import lifestyle_agree_groups

    ratio = pd.Series([0.0, 0.0, 0.5, 0.5, 1.0, 1.0, np.nan, np.nan, 0.25, 0.75])
    known = pd.Series([2, 2, 2, 2, 2, 2, 0, 0, 4, 4])
    groups = lifestyle_agree_groups(
        pd.DataFrame({"lifestyle_agree_ratio": ratio, "lifestyle_known_count": known})
    )
    assert (groups[known == 0] == "brak danych").all()
    assert (groups[known > 0] != "brak danych").all()
    # tercile boundaries come from known rows only: the two NaN rows are not counted as zeros
    low = groups[known > 0].iloc[:2]
    assert (low == groups[known > 0].iloc[0]).all()


def test_sample_funnel_counts_each_exclusion_step():
    df = pd.DataFrame(
        {
            "user_key": ["a", "a", "b", "c", "d"],
            "target_user_key": ["x", "y", "x", "z", "z"],
            "y_right": [1, 0, 0, 1, 0],
            "age_band_diff": [0.0, 1.0, np.nan, 2.0, 1.0],
            "lifestyle_agree_ratio": [0.5, np.nan, 0.5, 1.0, 0.0],
        }
    )
    funnel = sample_funnel(df, n_all_swipes=10, n_profile_swipes=7).set_index("step")
    assert list(funnel["swipes"]) == [10, 7, 5, 4, 3]
    assert funnel.iloc[-1]["swipes"] == 3  # age known AND >=1 lifestyle field known
    assert list(funnel["dropped"])[1:] == [3, 2, 1, 1]
