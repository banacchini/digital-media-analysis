"""Analysis (b): Reciprocity — observed vs expected matches.

Universe: unordered pairs {A, B} where both A→B and B→A are in the dataset.
Expected matches: sum of p̂_AB * p̂_BA (under independence).
Observed matches: pairs where both y_right_A=1 and y_right_B=1.

Main analysis excludes the 246 pairs with one recorded swipe (G15).
Sensitivity: those pairs added as matches.

NOTE: Results are described as "behaviour conditional on exposure" (G1 caveat).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .eval import BOOTSTRAP_REPS, SEED

logger = logging.getLogger(__name__)


def build_pair_universe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Return dataframe of unordered pairs {A,B} with both directed edges.

    Columns: pair_id (int), y_right_A, y_right_B
    (A is defined as the lexicographically smaller internal sender_idx)
    """
    pair_A = df[["user_key", "target_user_key", "y_right", "sender_idx", "receiver_idx"]].copy()
    pair_B = df[["user_key", "target_user_key", "y_right", "sender_idx", "receiver_idx"]].rename(
        columns={
            "user_key": "target_user_key",
            "target_user_key": "user_key",
            "y_right": "y_right_B",
            "sender_idx": "receiver_idx",
            "receiver_idx": "sender_idx",
        }
    )
    both = pair_A.merge(pair_B, on=["user_key", "target_user_key"], suffixes=("", "_rev"))

    # Keep only one direction (A < B by user_key to avoid duplicates)
    both["_uid_A"] = both["sender_idx"]
    both["_uid_B"] = both["receiver_idx_rev"]
    both = both[both["_uid_A"] < both["_uid_B"]].copy()
    both = both.reset_index(drop=True)
    both["pair_id"] = np.arange(len(both))
    both["match_observed"] = (both["y_right"] == 1) & (both["y_right_B"] == 1)

    logger.info(
        "Pair universe: %d unordered pairs, %d observed matches",
        len(both),
        both["match_observed"].sum(),
    )
    return both[
        [
            "pair_id",
            "user_key",
            "target_user_key",
            "y_right",
            "y_right_B",
            "match_observed",
            "_uid_A",
            "_uid_B",
        ]
    ]


def add_predicted_probs(
    pair_df: pd.DataFrame,
    prob_AB: np.ndarray,
    prob_BA: np.ndarray,
) -> pd.DataFrame:
    """Add predicted probabilities and expected matches to pair_df.

    Parameters
    ----------
    prob_AB : p̂(A→B = right), indexed by pair_df order
    prob_BA : p̂(B→A = right), indexed by pair_df order
    """
    pair_df = pair_df.copy()
    pair_df["prob_AB"] = prob_AB
    pair_df["prob_BA"] = prob_BA
    pair_df["expected_match"] = prob_AB * prob_BA
    return pair_df


def reciprocity_summary(pair_df: pd.DataFrame) -> dict:
    """Compute observed vs expected matches with node bootstrap CI.

    Returns dict with main statistics.
    """
    observed = int(pair_df["match_observed"].sum())
    expected = float(pair_df["expected_match"].sum())
    ratio = observed / expected if expected > 0 else float("nan")

    # Node bootstrap: sample users (uid_A ∪ uid_B), retain induced pairs
    rng = np.random.default_rng(SEED)
    all_users = np.unique(np.concatenate([pair_df["_uid_A"].values, pair_df["_uid_B"].values]))
    n_users = len(all_users)

    boot_ratios = []
    for _ in range(BOOTSTRAP_REPS):
        sampled = set(rng.choice(all_users, size=n_users, replace=True))
        mask = pair_df["_uid_A"].isin(sampled) & pair_df["_uid_B"].isin(sampled)
        sub = pair_df[mask]
        if len(sub) == 0:
            continue
        obs_b = sub["match_observed"].sum()
        exp_b = sub["expected_match"].sum()
        boot_ratios.append(obs_b / max(exp_b, 1e-10))

    ci_lo = float(np.percentile(boot_ratios, 2.5))
    ci_hi = float(np.percentile(boot_ratios, 97.5))

    result = {
        "n_pairs": len(pair_df),
        "observed_matches": observed,
        "expected_matches": expected,
        "ratio_obs_exp": ratio,
        "bootstrap_ci_lo": ci_lo,
        "bootstrap_ci_hi": ci_hi,
    }
    logger.info(
        "Reciprocity: observed=%d, expected=%.1f, ratio=%.3f [%.3f, %.3f]",
        observed,
        expected,
        ratio,
        ci_lo,
        ci_hi,
    )
    return result


def reciprocity_by_expected_bins(pair_df: pd.DataFrame, n_bins: int = 5) -> pd.DataFrame:
    """Break down observed vs expected matches by bins of expected match probability.

    Suppress cells with < 5 pairs.
    """
    pair_df = pair_df.copy()
    pair_df["expected_bin"] = pd.qcut(pair_df["expected_match"], q=n_bins, duplicates="drop")

    rows = []
    for label, grp in pair_df.groupby("expected_bin", observed=True):
        if len(grp) < 5:
            continue
        rows.append(
            {
                "expected_bin": str(label),
                "n_pairs": len(grp),
                "observed_matches": int(grp["match_observed"].sum()),
                "expected_matches": float(grp["expected_match"].sum()),
                "ratio": grp["match_observed"].sum() / max(grp["expected_match"].sum(), 1e-10),
            }
        )
    return pd.DataFrame(rows)


def calibration_check_universe(pair_df: pd.DataFrame) -> dict:
    """Check if p̂ is well-calibrated on the pair universe (all edges).

    If p̂ is biased here, expected match count is biased. Document finding.
    """
    # On the pair universe, check calibration of p_AB and p_BA separately
    for col, name in [("prob_AB", "A→B"), ("prob_BA", "B→A")]:
        if col not in pair_df.columns:
            continue
        from .eval import compute_calibration

        y = pair_df["y_right" if col == "prob_AB" else "y_right_B"].to_numpy()
        p = pair_df[col].to_numpy()
        _, mp, ma = compute_calibration(y, p, n_bins=5)
        logger.info("Calibration on pair universe (%s): mean_pred=%s, mean_actual=%s", name, mp, ma)

    return {"note": "see logs for calibration on pair universe"}
