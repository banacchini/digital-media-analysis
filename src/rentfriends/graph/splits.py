"""Train/test splits for graph analysis.

P1 (transductive): 5-fold edge-stratified by sender.
P2 (cold-start):   5-fold GroupKFold by sender.
Pair folds:        unordered pair {A,B} always in the same fold.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

logger = logging.getLogger(__name__)

SEED = 42
N_FOLDS = 5
MIN_TRAIN_EDGES = 5  # min training edges for sender/receiver to be evaluated in P1


# ---------------------------------------------------------------------------
# P1: Transductive splits (edge-stratified by sender)
# ---------------------------------------------------------------------------


def make_p1_folds(df: pd.DataFrame, seed: int = SEED) -> list[tuple[np.ndarray, np.ndarray]]:
    """5-fold edge-level splits stratified by sender.

    Each sender's edges are randomly assigned to one of 5 folds (stratified on y_right).
    Returns list of (train_idx, test_idx) tuples (integer positions into df).
    """
    rng = np.random.default_rng(seed)
    df = df.reset_index(drop=True)
    n = len(df)
    fold_assignments = np.full(n, -1, dtype=int)

    for _sender_idx, group in df.groupby("sender_idx"):
        idx = group.index.to_numpy()
        y = group["y_right"].to_numpy()
        n_g = len(idx)
        if n_g < N_FOLDS:
            # Assign randomly if too few edges
            folds = rng.integers(0, N_FOLDS, size=n_g)
        else:
            # Stratify on y_right if possible
            pos = idx[y == 1]
            neg = idx[y == 0]
            folds_pos = rng.permutation(len(pos)) % N_FOLDS
            folds_neg = rng.permutation(len(neg)) % N_FOLDS
            fold_assignments[pos] = folds_pos
            fold_assignments[neg] = folds_neg
            continue
        fold_assignments[idx] = folds

    # Fill any -1 (shouldn't happen)
    unfilled = fold_assignments == -1
    if unfilled.any():
        fold_assignments[unfilled] = rng.integers(0, N_FOLDS, size=unfilled.sum())

    # Build (train_idx, test_idx) for each fold
    all_positions = np.arange(n)
    folds = []
    for k in range(N_FOLDS):
        test_mask = fold_assignments == k
        train_mask = ~test_mask
        folds.append((all_positions[train_mask], all_positions[test_mask]))

    logger.info("P1 folds built: %d folds, seed=%d", N_FOLDS, seed)
    return folds


def p1_eval_mask(df: pd.DataFrame, train_idx: np.ndarray) -> np.ndarray:
    """Return boolean mask for test edges where both sender and receiver have ≥ MIN_TRAIN_EDGES.

    Call with the full df and training indices of a given fold.
    Returns boolean array of length len(df) (True = evaluate this test edge).
    """
    train_df = df.iloc[train_idx]
    sender_counts = train_df.groupby("sender_idx").size()
    receiver_counts = train_df.groupby("receiver_idx").size()

    sender_ok = df["sender_idx"].map(sender_counts).fillna(0) >= MIN_TRAIN_EDGES
    receiver_ok = df["receiver_idx"].map(receiver_counts).fillna(0) >= MIN_TRAIN_EDGES

    eval_mask = (sender_ok & receiver_ok).to_numpy()
    len(df) - len(train_idx)
    eval_mask.sum() - len(train_idx)  # only count test edges
    # Actually compute properly
    test_mask = np.ones(len(df), dtype=bool)
    test_mask[train_idx] = False
    eval_mask_test = eval_mask & test_mask
    n_excluded = test_mask.sum() - eval_mask_test.sum()
    frac_excluded = n_excluded / max(test_mask.sum(), 1)
    logger.info(
        "P1 eval mask: %d / %d test edges excluded (%.1f%% — sender or receiver < %d train edges)",
        n_excluded,
        test_mask.sum(),
        100 * frac_excluded,
        MIN_TRAIN_EDGES,
    )
    return eval_mask_test


# ---------------------------------------------------------------------------
# P2: Cold-start splits (GroupKFold by sender)
# ---------------------------------------------------------------------------


def make_p2_folds(df: pd.DataFrame, seed: int = SEED) -> list[tuple[np.ndarray, np.ndarray]]:
    """5-fold GroupKFold by sender_idx.

    Returns list of (train_idx, test_idx) tuples (integer positions).
    """
    gkf = GroupKFold(n_splits=N_FOLDS)
    all_positions = np.arange(len(df))
    groups = df["sender_idx"].to_numpy()
    folds = [
        (train_pos, test_pos) for train_pos, test_pos in gkf.split(all_positions, groups=groups)
    ]
    logger.info("P2 folds built: %d folds (GroupKFold by sender)", N_FOLDS)
    return folds


# ---------------------------------------------------------------------------
# Pair folds: unordered {A,B} always in the same fold
# ---------------------------------------------------------------------------


def make_pair_folds(df: pd.DataFrame, seed: int = SEED) -> list[tuple[np.ndarray, np.ndarray]]:
    """5-fold splits where unordered pair {A,B} is always in the same fold.

    Universe: rows in df where the reverse edge B→A also exists.
    Returns list of (train_idx, test_idx) for the full df (non-pair edges assigned to train).
    """
    rng = np.random.default_rng(seed)

    # Find rows that belong to a reciprocal pair
    pair_key = df.apply(lambda r: tuple(sorted([r["user_key"], r["target_user_key"]])), axis=1)
    df = df.copy()
    df["_pair_key"] = pair_key

    # Count pair occurrences: pairs with exactly 2 directed edges
    pair_counts = df["_pair_key"].value_counts()
    reciprocal_pairs = set(pair_counts[pair_counts == 2].index)
    df["_pair_key"].isin(reciprocal_pairs)

    # Assign fold to each unordered pair
    unique_pairs = list(reciprocal_pairs)
    rng.shuffle(unique_pairs)
    pair_fold = {p: i % N_FOLDS for i, p in enumerate(unique_pairs)}

    fold_assignment = df["_pair_key"].map(pair_fold)
    # Non-reciprocal edges: put in train always
    fold_assignment = fold_assignment.fillna(-1).astype(int)

    all_positions = np.arange(len(df))
    folds = []
    for k in range(N_FOLDS):
        test_mask = fold_assignment == k
        train_mask = ~test_mask  # includes non-reciprocal (fold=-1) always in train
        folds.append((all_positions[train_mask], all_positions[test_mask]))

    n_pairs = len(reciprocal_pairs)
    logger.info("Pair folds built: %d unordered pairs, %d folds", n_pairs, N_FOLDS)
    return folds


def validate_pair_fold_no_leakage(
    df: pd.DataFrame, folds: list[tuple[np.ndarray, np.ndarray]]
) -> None:
    """Assert that for each fold, no test edge's reverse appears in training adjacency."""
    df = df.copy()
    df["_pair_key"] = df.apply(
        lambda r: tuple(sorted([r["user_key"], r["target_user_key"]])), axis=1
    )
    for k, (train_idx, test_idx) in enumerate(folds):
        test_pairs = set(df.iloc[test_idx]["_pair_key"])
        train_pairs = set(df.iloc[train_idx]["_pair_key"])
        overlap = test_pairs & train_pairs
        if overlap:
            raise AssertionError(f"Fold {k}: {len(overlap)} pairs appear in both train and test!")
    logger.info("Pair fold leakage check passed: all folds clean.")


def validate_p1_no_test_in_adjacency(
    df: pd.DataFrame, folds: list[tuple[np.ndarray, np.ndarray]]
) -> None:
    """Assert that test edges are not in the training adjacency matrix for each P1 fold."""
    for k, (train_idx, test_idx) in enumerate(folds):
        train_edges = set(
            zip(df.iloc[train_idx]["sender_idx"], df.iloc[train_idx]["receiver_idx"], strict=False)
        )
        test_edges = set(
            zip(df.iloc[test_idx]["sender_idx"], df.iloc[test_idx]["receiver_idx"], strict=False)
        )
        overlap = train_edges & test_edges
        if overlap:
            raise AssertionError(
                f"P1 fold {k}: {len(overlap)} test edges also in training adjacency!"
            )
    logger.info("P1 adjacency leak check passed.")
