"""D15 (`lifestyle_tag_conflict`): synthetic checks of the definition and the prevalence tools."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rentfriends import dataset_h1 as d1
from rentfriends import h1_d15 as d15

PAIRS = [({"smoker"}, {"non_smoker"}), ({"calm"}, {"party", "loud"})]


def _sets(rows):
    return [frozenset(r) for r in rows]


def test_conflict_counts_known_opposite_side_pairs():
    sender = _sets([["smoker"], ["non_smoker"], ["calm"], ["party"], ["smoker", "calm"]])
    receiver = _sets([["non_smoker"], ["smoker"], ["loud"], ["calm"], ["non_smoker", "party"]])
    # pairs 0..3 are opposite in exactly one group each; pair 4 is opposite in both groups
    flags = d15.group_conflicts(sender, receiver, PAIRS)
    assert flags.sum(axis=0).tolist() == [3, 3]
    assert flags.any(axis=1).sum() == 5
    assert flags[4].tolist() == [True, True]


def test_same_side_is_not_a_conflict():
    sender = _sets([["smoker"], ["calm"], ["party"], ["loud", "party"]])
    receiver = _sets([["smoker"], ["calm"], ["loud"], ["party"]])
    assert not d15.group_conflicts(sender, receiver, PAIRS).any()


def test_missing_tags_are_not_a_conflict():
    sender = _sets([[], ["smoker"], [], ["unrelated"]])
    receiver = _sets([[], [], ["non_smoker"], ["non_smoker"]])
    assert not d15.group_conflicts(sender, receiver, PAIRS).any()


def test_nan_and_none_tags_are_not_a_conflict():
    # missing profile data must neither crash nor count as a conflict
    assert d1.compute_lifestyle_tag_conflict(np.nan, ["non_smoker"]) == 0
    assert d1.compute_lifestyle_tag_conflict(["smoker"], None) == 0
    assert d1.compute_lifestyle_tag_conflict(None, np.nan) == 0
    sender = d15.as_tag_sets([np.nan, None, ["smoker"]])
    receiver = d15.as_tag_sets([["non_smoker"], ["non_smoker"], np.nan])
    assert not d15.group_conflicts(sender, receiver, PAIRS).any()


def _random_sets(rng, vocab, n):
    return [frozenset(rng.choice(vocab, size=rng.integers(0, 4), replace=False)) for _ in range(n)]


def test_production_function_agrees_with_vectorised_flags():
    rng = np.random.default_rng(0)
    vocab = ["smoker", "non_smoker", "early_bird", "night_owl", "animals", "no_pets", "x", "y"]
    sender, receiver = _random_sets(rng, vocab, 300), _random_sets(rng, vocab, 300)
    stored = np.array(
        [
            d1.compute_lifestyle_tag_conflict(list(a), list(b))
            for a, b in zip(sender, receiver, strict=True)
        ]
    )
    flags = d15.group_conflicts(sender, receiver, d1.POLARITY_PAIRS)
    assert (flags.any(axis=1).astype(int) == stored).all()


def test_prevalence_table_reports_group_rates():
    sender = _sets([["smoker"], ["non_smoker"], [], ["calm"]])
    receiver = _sets([["non_smoker"], ["non_smoker"], ["smoker"], ["party"]])
    tbl = d15.prevalence_table(sender, receiver, PAIRS)
    assert tbl.loc[0, "conflict_rate"] == pytest.approx(0.25)  # only pair 0
    assert tbl.loc[1, "conflict_rate"] == pytest.approx(0.25)  # only pair 3
    assert tbl.loc[0, "sender_any_tag"] == pytest.approx(0.5)
    assert tbl.loc[0, "receiver_any_tag"] == pytest.approx(0.75)
    assert tbl.loc["any", "conflict_rate"] == pytest.approx(0.5)


def _random_smoking_sets(rng, n):
    def one():
        if rng.random() < 0.3:
            return frozenset(["smoker"])
        return frozenset(["non_smoker"] if rng.random() < 0.5 else [])

    return [one() for _ in range(n)]


def test_independence_baseline_matches_observed_when_sides_are_independent():
    rng = np.random.default_rng(1)
    s, r = _random_smoking_sets(rng, 20_000), _random_smoking_sets(rng, 20_000)
    out = d15.independence_baseline(s, r, PAIRS[:1], n_perm=50, seed=0)
    observed = d15.group_conflicts(s, r, PAIRS[:1]).mean()
    assert out["any"]["perm_mean"] == pytest.approx(observed, abs=0.01)


def test_independence_baseline_detects_dependence():
    # perfectly opposite pairs: observed conflict is 1, independence baseline is about 0.5
    n = 4_000
    rng = np.random.default_rng(2)
    flip = rng.random(n) < 0.5
    s = [frozenset(["smoker"] if f else ["non_smoker"]) for f in flip]
    r = [frozenset(["non_smoker"] if f else ["smoker"]) for f in flip]
    out = d15.independence_baseline(s, r, PAIRS[:1], n_perm=50, seed=0)
    assert out["any"]["observed"] == pytest.approx(1.0)
    assert out["any"]["perm_mean"] == pytest.approx(0.5, abs=0.03)


def test_prevalence_frame_is_aggregate_only():
    sender = _sets([["smoker"], ["calm"]])
    receiver = _sets([["non_smoker"], ["party"]])
    tbl = d15.prevalence_table(sender, receiver, PAIRS)
    assert isinstance(tbl, pd.DataFrame)
    assert {"conflict_rate", "sender_any_tag", "receiver_any_tag"} <= set(tbl.columns)
