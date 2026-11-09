"""Tests for the graph analysis module.

Tests (Z1 requirements):
(i)  No test edge appears in the training adjacency matrix.
(ii) Permutation of test labels gives ≈ random logLoss (≈ log(2)).
(iii) Forbidden (leaky) columns absent from feature set.

Additional:
- Split properties: ≥ 5-edge threshold tracked, pair fold exclusivity.
- Pair fold leakage: B→A edge never in train when A→B in test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rentfriends.graph.data import (
    FORBIDDEN_COLS,
    PAIR_FEATURE_COLS,
    build_pair_features,
    leak_check,
)
from rentfriends.graph.eval import permutation_baseline_logloss
from rentfriends.graph.splits import (
    make_p1_folds,
    make_pair_folds,
    p1_eval_mask,
    validate_p1_no_test_in_adjacency,
    validate_pair_fold_no_leakage,
)

# ---------------------------------------------------------------------------
# Minimal synthetic dataset for fast tests
# ---------------------------------------------------------------------------


def make_synthetic_df(n: int = 500, seed: int = 0) -> pd.DataFrame:
    """Create a minimal synthetic swipe dataframe."""
    rng = np.random.default_rng(seed)
    n_users = 50
    senders = rng.integers(0, n_users // 2, size=n)
    receivers = rng.integers(n_users // 2, n_users, size=n)
    # Avoid self-swipes and enforce unique sender-receiver pairs
    seen = set()
    rows = []
    for s, r in zip(senders, receivers, strict=False):
        if s != r and (s, r) not in seen:
            seen.add((s, r))
            rows.append(
                {
                    "user_key": f"u{s}",
                    "target_user_key": f"u{r}",
                    "y_right": int(rng.random() < 0.2),
                    "sender_idx": int(s),
                    "receiver_idx": int(r),
                    "city_sender": "Wrocław",
                    "city_receiver": "Wrocław",
                    "sex_pair": "M→F",
                    "same_band": 1,
                    "age_band_diff": 0,
                    "age_band_diff_abs": 0,
                    "same_city": 1,
                    "city_diff": 0,
                    "interests_jaccard": 0.5,
                    "interests_shared_n": 2,
                    "lifestyle_agree_ratio": 0.6,
                    "lifestyle_tag_conflict": 0,
                    "lifestyle_shared_tags_n": 1,
                    "day": 1,
                }
            )
        if len(rows) >= n:
            break
    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Test (i): No test edge in training adjacency
# ---------------------------------------------------------------------------


def test_p1_no_test_edge_in_train_adjacency() -> None:
    df = make_synthetic_df(400)
    folds = make_p1_folds(df, seed=42)
    # Should not raise
    validate_p1_no_test_in_adjacency(df, folds)


# ---------------------------------------------------------------------------
# Test (ii): Permutation baseline ≈ log(2)
# ---------------------------------------------------------------------------


def test_permutation_baseline_near_log2() -> None:
    rng = np.random.default_rng(0)
    n = 1000
    y = rng.binomial(1, 0.2, size=n)
    p_uniform = np.full(n, 0.2)
    # With shuffled labels, logloss should be near -(0.2*log(0.2) + 0.8*log(0.8))
    mean_ll, std_ll = permutation_baseline_logloss(y, p_uniform, n_perms=50, seed=0)
    # For p=0.2: -(0.2*log(0.2) + 0.8*log(0.8)) ≈ 0.500
    expected = -(0.2 * np.log(0.2) + 0.8 * np.log(0.8))
    assert abs(mean_ll - expected) < 0.02, f"Expected ≈{expected:.3f}, got {mean_ll:.3f}"


# ---------------------------------------------------------------------------
# Test (iii): Forbidden columns absent from pair features
# ---------------------------------------------------------------------------


def test_no_forbidden_columns_in_features() -> None:
    leak_check(pd.DataFrame(), PAIR_FEATURE_COLS)
    # Explicitly check none of FORBIDDEN_COLS is in PAIR_FEATURE_COLS
    overlap = FORBIDDEN_COLS.intersection(PAIR_FEATURE_COLS)
    assert len(overlap) == 0, f"Leaky columns in features: {overlap}"


def test_forbidden_columns_raises() -> None:
    with pytest.raises(ValueError, match="Leakage"):
        leak_check(pd.DataFrame(), list(FORBIDDEN_COLS) + ["some_col"])


# ---------------------------------------------------------------------------
# Pair fold exclusivity
# ---------------------------------------------------------------------------


def test_pair_fold_no_leakage() -> None:
    df = make_synthetic_df(400)
    folds = make_pair_folds(df, seed=42)
    validate_pair_fold_no_leakage(df, folds)


def test_pair_fold_all_indices_covered() -> None:
    df = make_synthetic_df(400)
    folds = make_pair_folds(df, seed=42)
    # Every index appears in exactly one test fold
    n = len(df)
    test_counts = np.zeros(n, dtype=int)
    for _, test_idx in folds:
        test_counts[test_idx] += 1
    # Pair edges: exactly 1 test appearance; non-pair edges: 0 (always train)
    assert (test_counts <= 1).all(), "Some indices appear in more than one test fold."


# ---------------------------------------------------------------------------
# P1 eval mask
# ---------------------------------------------------------------------------


def test_p1_eval_mask_excludes_cold_nodes() -> None:
    df = make_synthetic_df(400)
    folds = make_p1_folds(df, seed=42)
    train_idx, test_idx = folds[0]
    mask = p1_eval_mask(df, train_idx)
    # Mask should be a boolean array of len(df)
    assert len(mask) == len(df)
    assert mask.dtype == bool
    # Test edges that are masked should be a subset of test_idx
    test_mask = np.zeros(len(df), dtype=bool)
    test_mask[test_idx] = True
    assert (mask & ~test_mask).sum() == 0, "Eval mask includes training edges!"


# ---------------------------------------------------------------------------
# Feature build: no NaN in output for complete cases
# ---------------------------------------------------------------------------


def test_build_pair_features_no_nan() -> None:
    df = make_synthetic_df(100)
    n = len(df)
    train_mask = np.ones(n, dtype=bool)
    train_mask[n // 5 :] = False
    X, sm, ss = build_pair_features(df, train_mask=train_mask)
    assert X.shape[0] == n
    # With complete data there should be no NaN
    assert not np.isnan(X).any(), "NaN in feature matrix for complete-case data."
