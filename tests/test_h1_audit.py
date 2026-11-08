"""Unit tests for the H1 audit helpers (age direction, block increments, bootstrap, ...)."""

import numpy as np
import pandas as pd

from conftest import make_dummy_h1_df
from rentfriends.h1_audit import (
    age_direction_check,
    block_increment_table,
    block_increments_from_fit,
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
