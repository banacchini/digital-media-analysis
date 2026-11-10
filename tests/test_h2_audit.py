"""Tests for the H2 audit module on simulated data (no access to data/)."""

import numpy as np
import pandas as pd

from rentfriends import h2
from rentfriends import h2_audit as A
from rentfriends.h2_cache import Cache, data_hash

BANDS = ["18-20", "21-23", "24-26", "27-30"]


def simulate(n_send=300, per=60, pi=0.7, h=0.25, age_pen=-0.4, seed=0) -> pd.DataFrame:
    """Swipes with logit = -1.5 + pi*rF + h*s*rF + age_pen*older (no random effects)."""
    rng = np.random.default_rng(seed)
    n_rec = 250
    s_sex = rng.choice(["F", "M"], n_send)
    s_band = rng.choice(BANDS, n_send, p=[0.5, 0.25, 0.15, 0.1])
    r_sex = rng.choice(["F", "M"], n_rec)
    r_band = rng.choice(BANDS, n_rec, p=[0.5, 0.25, 0.15, 0.1])
    si = np.repeat(np.arange(n_send), per)
    ri = rng.integers(0, n_rec, size=len(si))
    snd, rcv = s_sex[si], r_sex[ri]
    bi = {b: i for i, b in enumerate(BANDS)}
    sb = np.array([bi[b] for b in s_band[si]])
    rb = np.array([bi[b] for b in r_band[ri]])
    diff = (rb - sb).astype(float)
    s = np.where(snd == "F", 1.0, -1.0)
    rf = (rcv == "F").astype(float)
    eta = -1.5 + pi * rf + h * s * rf + age_pen * np.clip(diff, 0, None)
    y = (rng.random(len(si)) < 1 / (1 + np.exp(-eta))).astype(int)
    df = pd.DataFrame(
        {
            "sender": [f"s{i}" for i in si],
            "receiver": [f"r{i}" for i in ri],
            "day": 1,
            "y_right": y,
            "sender_sex": snd,
            "receiver_sex": rcv,
            "sender_band": s_band[si],
            "receiver_band": r_band[ri],
            "sender_city": "Wrocław",
            "receiver_city": "Wrocław",
        }
    )
    return h2.add_demography(df)


def test_sex_decomposition_recovers_pi_and_h():
    d = A.sex_sample(A.prepare(simulate(pi=0.7, h=0.25)))
    fit = A.z1_fit(d, controls=False, glmm=False)
    der = A.z1_derived(fit).set_index("quantity")
    assert abs(der.loc["pi: popularność profili F (przy symetrii)", "log_or"] - 0.7) < 0.12
    assert abs(der.loc["h: premia za własną płeć (przy symetrii)", "log_or"] - 0.25) < 0.12


def test_gaps_match_pi_plus_minus_h_and_ratio_is_2h():
    d = A.sex_sample(A.prepare(simulate(pi=0.5, h=0.3, seed=1)))
    der = A.z1_derived(A.z1_fit(d, controls=False, glmm=False)).set_index("quantity")
    pi = der.loc["pi: popularność profili F (przy symetrii)", "log_or"]
    h = der.loc["h: premia za własną płeć (przy symetrii)", "log_or"]
    gf = der.loc["gap_F: odbiorca F vs M, nadawcy F", "log_or"]
    gm = der.loc["gap_M: odbiorca F vs M, nadawcy M", "log_or"]
    assert np.isclose(gf, pi + h, atol=1e-6)
    assert np.isclose(gm, pi - h, atol=1e-6)
    assert np.isclose(der.loc["ratio_of_gaps = 2h (bez założeń)", "log_or"], 2 * h)


def test_sex_o_is_excluded_from_z1_sample():
    df = simulate()
    df.loc[df.index[:50], "receiver_sex"] = "O"
    d = A.sex_sample(A.prepare(df))
    assert set(d["receiver_sex"]) == {"F", "M"}


def test_age_matrix_suppresses_small_cells():
    d = A.age_sample(A.prepare(simulate(n_send=200)))
    # make one cell reachable by only 2 senders
    keep = d[(d["sender_band4"] != "27+") | (d["sender_code"] < 2)]
    m = A.age_matrix(keep, n_boot=50, seed=0)
    small = m[m["sender_band"] == "27+"]
    assert small["suppressed"].all()
    assert small[["n", "k", "rate", "ci_low", "ci_high", "n_senders"]].isna().all().all()
    assert (~m[m["sender_band"] == "18-20"]["suppressed"]).all()


def test_age_matrix_has_no_user_keys():
    d = A.age_sample(A.prepare(simulate(n_send=100)))
    m = A.age_matrix(d, n_boot=20, seed=0)
    assert not {"sender", "receiver", "user_key"} & set(m.columns)


def test_age_models_older_penalty_sign():
    d = A.age_sample(A.prepare(simulate(age_pen=-0.5, seed=2)))
    dd, X, y, names = A.age_design(d, "dir", fe_band=True)
    est = A.estimate(
        X, y, dd["sender_code"].to_numpy(), dd["receiver_code"].to_numpy(), names, glmm=False
    )
    t = A.term_table(est, "dir").set_index("term")
    assert t.loc["older_per_band", "or"] < 0.8
    assert est["primary"] == "pooled (fallback)"


def test_linear_and_direction_parametrisations_are_the_same_model():
    d = A.age_sample(A.prepare(simulate(seed=3)))
    ll = []
    for param in ("linear", "dir"):
        dd, X, y, names = A.age_design(d, param, fe_band=False)
        est = A.estimate(
            X, y, dd["sender_code"].to_numpy(), dd["receiver_code"].to_numpy(), names, glmm=False
        )
        ll.append(est["pooled"]["loglik"])
    assert np.isclose(ll[0], ll[1], atol=1e-6)


def test_cv_null_model_has_chance_auc_and_pr_equal_to_prevalence():
    d = A.prepare(simulate(n_send=150))
    oof = A.cv_oof(d, "sender", 5, 0)
    s = A.cv_summary(oof, n_boot=20, seed=0)
    m = s["metrics"].set_index(["block", "metric"])
    assert abs(m.loc[("null", "auc"), "value"] - 0.5) < 1e-9
    assert abs(m.loc[("null", "auc_pr"), "value"] - oof["y"].mean()) < 1e-6


def test_cv_group_by_receiver_keeps_receivers_out_of_train():
    d = A.prepare(simulate(n_send=120))
    oof = A.cv_oof(d, "receiver", 5, 0)
    dd = d.dropna(subset=["sex_pair", "age_band_diff", "same_band"]).reset_index(drop=True)
    per_rec = pd.DataFrame({"r": dd["receiver"], "f": oof["folds"]}).groupby("r")["f"].nunique()
    assert (per_rec == 1).all()


def test_cv_deltas_have_ordered_ci():
    d = A.prepare(simulate(n_send=150, seed=4))
    s = A.cv_summary(A.cv_oof(d, "sender", 5, 1), n_boot=30, seed=1)
    de = s["deltas"]
    assert (de["ci_low"] <= de["ci_high"]).all()
    assert set(de["metric"]) == {"logloss", "auc", "auc_pr"}


def test_cache_hit_skips_recompute_and_key_depends_on_params(tmp_path):
    c = Cache(tmp_path)
    calls = []

    def fn():
        calls.append(1)
        return {"x": 1}

    df = pd.DataFrame({"a": [1, 2, 3]})
    h = data_hash(df, ["a"])
    assert c.get("s", fn, dhash=h, params={"k": 1}) == {"x": 1}
    assert c.get("s", fn, dhash=h, params={"k": 1}) == {"x": 1}
    assert len(calls) == 1
    c.get("s", fn, dhash=h, params={"k": 2})
    assert len(calls) == 2
    c.get("s", fn, dhash=data_hash(df.assign(a=[1, 2, 4]), ["a"]), params={"k": 1})
    assert len(calls) == 3
    assert c.clear("s") == 3


def test_term_table_marks_missing_glmm_se_as_unavailable():
    est = {
        "pooled": {"names": ["const", "x"], "coef": [0.0, 0.5], "se": [0.1, 0.2]},
        "glmm": {"names": ["const", "x"], "coef": [0.0, 0.9], "se": [float("nan")] * 2},
        "glmm_ok": False,
    }
    t = A.term_table(est, "m").set_index("estimator")
    assert not t.loc["GLMM (warunkowe)", "converged_with_se"]
    assert np.isnan(t.loc["GLMM (warunkowe)", "or_lo"])
    assert np.isfinite(t.loc["pooled (populacyjne)", "or_lo"])
