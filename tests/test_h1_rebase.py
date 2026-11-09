"""Block-increment bootstrap summaries, dictionary sensitivity and tag decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rentfriends import h1_audit, h1_rebase

BLOCK_DF = {"age": 3, "interests": 3, "lifestyle": 3}
MODELS = [
    "controls",
    "age",
    "interests",
    "lifestyle",
    "age_interests",
    "age_lifestyle",
    "interests_lifestyle",
    "full",
]


def _ll_frame(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = -1000.0 + np.cumsum(np.abs(rng.normal(size=(n, len(MODELS)))), axis=1)
    return pd.DataFrame(base, columns=MODELS)


def test_vectorised_increments_match_the_audit_table():
    ll = _ll_frame()
    draws = h1_rebase.increment_draws(ll)
    for i in (0, 7, 39):
        tbl = h1_audit.block_increment_table(ll.iloc[i].to_dict(), BLOCK_DF).set_index("block")
        for block in ("age", "interests", "lifestyle", "age+interests"):
            for d in ("first", "last", "mean"):
                assert draws[(f"dll: {block}", d)][i] == pytest.approx(tbl.loc[block, f"dll_{d}"])


def test_block_means_add_up_to_the_full_model_gain():
    ll = _ll_frame()
    d = h1_rebase.increment_draws(ll)
    total = sum(d[(f"dll: {b}", "mean")] for b in ("age", "interests", "lifestyle"))
    assert total == pytest.approx((ll["full"] - ll["controls"]).to_numpy())


def test_quantities_contain_contrasts_ratio_and_age_share():
    q = h1_rebase.quantity_draws(h1_rebase.increment_draws(_ll_frame()))
    assert ("diff: lifestyle - interests", "mean") in q
    assert ("ratio: lifestyle / interests", "mean") in q
    assert ("share: age", "mean") in q
    assert np.all((q[("share: age", "mean")] > 0) & (q[("share: age", "mean")] < 1))


def test_summarise_uses_percentiles_of_the_draws():
    obs = {("dll: x", "mean"): np.array([5.0])}
    boot = {("dll: x", "mean"): np.linspace(0, 10, 101)}
    out = h1_rebase.summarise_quantities(obs, boot, level=0.9).iloc[0]
    assert out["estimate"] == 5.0
    assert out["ci_low"] == pytest.approx(0.5) and out["ci_high"] == pytest.approx(9.5)


def test_conservative_ci_takes_the_wider_interval():
    base = {"quantity": ["q", "r"], "definition": ["mean", "mean"], "estimate": [1.0, 2.0]}
    s = pd.DataFrame({**base, "ci_low": [0.0, 1.0], "ci_high": [2.0, 3.0], "boot_se": [1.0, 1.0]})
    r = pd.DataFrame({**base, "ci_low": [-1.0, 1.5], "ci_high": [3.0, 2.5], "boot_se": [2.0, 0.5]})
    out = h1_rebase.conservative_ci(s, r).set_index("quantity")
    assert (out.loc["q", "ci_low"], out.loc["q", "ci_high"], out.loc["q", "wider_is"]) == (
        -1.0,
        3.0,
        "receiver",
    )
    assert (out.loc["r", "ci_low"], out.loc["r", "ci_high"], out.loc["r", "wider_is"]) == (
        1.0,
        3.0,
        "sender",
    )
    assert bool(out.loc["q", "excludes_zero"]) is False and bool(out.loc["r", "excludes_zero"])


def test_change_between_scenarios_is_paired_draw_by_draw():
    key = ("q", "mean")
    out = h1_rebase.summarise_change(
        {key: np.array([1.0])},
        {key: np.array([1.0, 2.0, 3.0, 4.0])},
        {key: np.array([3.0])},
        {key: np.array([2.0, 4.0, 6.0, 8.0])},
        level=0.5,
    ).iloc[0]
    assert out["estimate"] == pytest.approx(2.0)  # observed change
    # paired draws: 2-1, 4-2, 6-3, 8-4 = 1, 2, 3, 4 -> central 50% = [1.75, 3.25]
    assert out["ci_low"] == pytest.approx(1.75) and out["ci_high"] == pytest.approx(3.25)


def test_single_tag_shift_changes_only_that_tag():
    agent = {"cooking": "hobby", "tech_it": "unclear"}
    final = {"cooking": "lifestyle", "tech_it": "unclear"}
    shifts = h1_rebase.single_category_shifts(["cooking", "tech_it"], agent, final)
    by_tag = {s.label: s for s in shifts}
    assert by_tag["cooking"].kwargs == {"category_override": {"cooking": "lifestyle"}}
    assert by_tag["tech_it"].kwargs is None  # same category as v0: nothing to refit


def test_single_merge_shifts_repoint_d13_and_polarity():
    shifts = h1_rebase.single_merge_shifts({"quiet_evenings": "likes_calm", "a": "b"})
    s = next(x for x in shifts if x.label == "quiet_evenings → likes_calm")
    assert s.kwargs["tag_merge"] == {"quiet_evenings": "likes_calm"}
    assert "likes_calm" in s.kwargs["polarity_pairs"][4][0]
    assert "quiet_evenings" not in s.kwargs["polarity_pairs"][4][0]


def test_dictionary_plot_is_written(tmp_path):
    tbl = pd.DataFrame(
        {
            "scenario": ["(i) v0", "(ii) A+B", "(vi) v1"],
            "estimate": [3.05, 1.71, 1.41],
            "ci_low": [1.5, 0.8, 0.7],
            "ci_high": [6.0, 3.5, 2.9],
        }
    )
    out = tmp_path / "plot.png"
    h1_rebase.plot_dictionary_sensitivity(tbl, out)
    assert out.exists() and out.stat().st_size > 1000
