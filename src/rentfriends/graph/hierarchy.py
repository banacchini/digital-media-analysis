"""Analysis (c): Hierarchy of desire.

Following Bruch & Newman (2018, Science Advances):
- Desire score D(u) = cross-fitted receiver effect (from M1) in percentiles.
- Sensitivity: PageRank on right-swipe edges from training folds.

Curves:
- P(right swipe | desire rank difference)
- P(B→A right | A→B right, desire rank difference) for reciprocal pairs
- Expected curve from p̂ (from M1)

Bins require ≥ 100 pairs; CI from node bootstrap.

CAVEAT: B's response is observed only where B was shown A (G1 — feed exposure unknown).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .eval import BOOTSTRAP_REPS, SEED

logger = logging.getLogger(__name__)

MIN_BIN_SIZE = 100  # minimum pairs per bin for curves


# ---------------------------------------------------------------------------
# Desire score
# ---------------------------------------------------------------------------


def compute_desire_scores(
    receiver_bias: np.ndarray,
    receiver_idx_unique: np.ndarray,
) -> pd.DataFrame:
    """Convert receiver effects to percentile desire scores.

    Parameters
    ----------
    receiver_bias : array of shape (n_receivers,) with cross-fitted receiver biases
    receiver_idx_unique : array of unique receiver indices (mapping to bias)

    Returns
    -------
    DataFrame with columns: receiver_idx, desire_score (raw), desire_pct (0–100)
    """
    df = pd.DataFrame(
        {
            "receiver_idx": receiver_idx_unique,
            "desire_score": receiver_bias,
        }
    )
    df["desire_pct"] = df["desire_score"].rank(pct=True) * 100
    return df


def compute_pagerank_desire(
    sender_idx: np.ndarray,
    receiver_idx: np.ndarray,
    right_mask: np.ndarray,
    n_senders: int,
    n_receivers: int,
    n_iter: int = 50,
    damping: float = 0.85,
) -> np.ndarray:
    """PageRank-based desire score on right-swipe edges (sensitivity).

    Uses training-fold right-swipe edges only.
    Returns array of shape (n_receivers,) with PageRank scores.
    """
    s = sender_idx[right_mask]
    r = receiver_idx[right_mask]
    if len(s) == 0:
        return np.zeros(n_receivers)

    # Build column-normalised adjacency (senders pointing to receivers)
    deg_s = np.bincount(s, minlength=n_senders).clip(min=1)
    # Transition: receiver ← (1/deg_s) * sender
    pr_r = np.ones(n_receivers) / n_receivers

    for _ in range(n_iter):
        # Aggregate: for each receiver, sum over senders
        new_pr_r = np.zeros(n_receivers)
        weights = 1.0 / deg_s[s]
        np.add.at(new_pr_r, r, weights)
        pr_r = damping * new_pr_r / max(new_pr_r.sum(), 1e-10) + (1 - damping) / n_receivers

    return pr_r


# ---------------------------------------------------------------------------
# League curves
# ---------------------------------------------------------------------------


def desire_rank_diff(
    df_edges: pd.DataFrame,
    desire_scores: pd.DataFrame,
    pair_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute desire rank differences for all edges.

    Parameters
    ----------
    df_edges     : swipe edges (must have sender_idx, receiver_idx, y_right)
    desire_scores: output of compute_desire_scores (receiver_idx, desire_pct)
    pair_df      : if provided, also compute for reciprocal pairs

    Returns DataFrame with: sender_idx, receiver_idx, y_right, desire_pct_receiver,
    desire_pct_sender (from receiver role), rank_diff
    """
    desire_map = desire_scores.set_index("receiver_idx")["desire_pct"].to_dict()
    df = df_edges.copy()
    df["desire_pct_receiver"] = df["receiver_idx"].map(desire_map)
    # Sender's own desire score (as receiver in reverse direction)
    df["desire_pct_sender"] = df["sender_idx"].map(desire_map)
    df["rank_diff"] = df["desire_pct_receiver"] - df["desire_pct_sender"]
    return df


def p_right_by_rank_diff(
    df: pd.DataFrame,
    n_bins: int = 10,
    group_col: str = "rank_diff",
    outcome_col: str = "y_right",
    user_idx_col: str = "sender_idx",
    seed: int = SEED,
) -> pd.DataFrame:
    """Empirical P(right swipe | rank difference) curve in equal-count bins.

    Suppress bins with < MIN_BIN_SIZE pairs.
    CI from node bootstrap.
    """
    df = df.dropna(subset=[group_col, outcome_col]).copy()
    df["_bin"] = pd.qcut(df[group_col], q=n_bins, duplicates="drop")

    rng = np.random.default_rng(seed)
    unique_users = df[user_idx_col].unique()

    rows = []
    for label, grp in df.groupby("_bin", observed=True):
        if len(grp) < MIN_BIN_SIZE:
            continue
        point = float(grp[outcome_col].mean())

        # Node bootstrap
        boot = []
        for _ in range(BOOTSTRAP_REPS):
            sampled = set(rng.choice(unique_users, size=len(unique_users), replace=True))
            sub = grp[grp[user_idx_col].isin(sampled)]
            if len(sub) == 0:
                continue
            boot.append(sub[outcome_col].mean())

        ci_lo = float(np.percentile(boot, 2.5)) if boot else float("nan")
        ci_hi = float(np.percentile(boot, 97.5)) if boot else float("nan")

        rows.append(
            {
                "bin_label": str(label),
                "bin_mid": float(grp[group_col].mean()),
                "n_pairs": len(grp),
                "p_right": point,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
            }
        )

    return pd.DataFrame(rows)


def p_reciprocate_by_rank_diff(
    pair_df: pd.DataFrame,
    desire_scores: pd.DataFrame,
    n_bins: int = 10,
    seed: int = SEED,
) -> pd.DataFrame:
    """P(B→A right | A→B right, rank difference) curve.

    Universe: pairs where A→B right (y_right=1).
    Conditional on A having swiped B right; B's response may not be observed (G1 caveat).
    """
    desire_map = desire_scores.set_index("receiver_idx")["desire_pct"].to_dict()
    df = pair_df[pair_df["y_right"] == 1].copy()  # A→B right

    df["desire_pct_B"] = df["_uid_B"].map(desire_map)
    df["desire_pct_A"] = df["_uid_A"].map(desire_map)
    df["rank_diff"] = df["desire_pct_B"] - df["desire_pct_A"]
    df = df.dropna(subset=["rank_diff", "y_right_B"]).copy()

    if len(df) < MIN_BIN_SIZE:
        logger.warning("Not enough pairs for reciprocate curve (n=%d < %d)", len(df), MIN_BIN_SIZE)
        return pd.DataFrame()

    rng = np.random.default_rng(seed)
    df["_bin"] = pd.qcut(df["rank_diff"], q=n_bins, duplicates="drop")

    rows = []
    for label, grp in df.groupby("_bin", observed=True):
        if len(grp) < MIN_BIN_SIZE:
            continue
        point = float(grp["y_right_B"].mean())

        all_users = np.unique(np.concatenate([grp["_uid_A"].values, grp["_uid_B"].values]))
        boot = []
        for _ in range(BOOTSTRAP_REPS):
            sampled = set(rng.choice(all_users, size=len(all_users), replace=True))
            sub = grp[grp["_uid_A"].isin(sampled) & grp["_uid_B"].isin(sampled)]
            if len(sub) == 0:
                continue
            boot.append(sub["y_right_B"].mean())

        ci_lo = float(np.percentile(boot, 2.5)) if boot else float("nan")
        ci_hi = float(np.percentile(boot, 97.5)) if boot else float("nan")

        rows.append(
            {
                "bin_label": str(label),
                "bin_mid": float(grp["rank_diff"].mean()),
                "n_pairs": len(grp),
                "p_reciprocate": point,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
            }
        )

    return pd.DataFrame(rows)
