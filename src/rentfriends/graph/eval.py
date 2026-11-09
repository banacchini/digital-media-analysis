"""Evaluation metrics and bootstrap CI for the graph analysis.

Metrics:
- logLoss (primary)
- AUC (secondary; not on poster)
- Lift@20% (poster metric)
- Calibration curve
"""

from __future__ import annotations

import logging

import numpy as np
from sklearn.metrics import log_loss, roc_auc_score

logger = logging.getLogger(__name__)

BOOTSTRAP_REPS = 1000
SEED = 42


# ---------------------------------------------------------------------------
# Point metrics
# ---------------------------------------------------------------------------


def compute_logloss(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Binary cross-entropy (nats)."""
    # Clip to avoid log(0)
    y_prob = np.clip(y_prob, 1e-7, 1 - 1e-7)
    return float(log_loss(y_true, y_prob))


def compute_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """ROC AUC. Returns NaN if only one class present."""
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_prob))


def compute_lift_at_20(y_true: np.ndarray, y_prob: np.ndarray, sender_idx: np.ndarray) -> float:
    """Weighted lift@20% across senders with ≥10 swipes and 0 < positives < total.

    For each eligible sender: sort profiles by predicted prob, take top 20%,
    compute precision. Compare to random baseline (sender's positive rate).
    Lift = precision_top20 / positive_rate.
    Returns weighted average lift (weighted by n_selected).
    """
    total_hits = 0
    total_selected = 0

    unique_senders = np.unique(sender_idx)
    for s in unique_senders:
        mask = sender_idx == s
        y_s = y_true[mask]
        p_s = y_prob[mask]
        n_s = len(y_s)
        pos_s = y_s.sum()

        # Eligibility: ≥10 swipes and 0 < positives < all
        if n_s < 10 or pos_s == 0 or pos_s == n_s:
            continue

        n_top = max(1, int(np.ceil(n_s * 0.20)))
        top_idx = np.argsort(p_s)[::-1][:n_top]
        hits = y_s[top_idx].sum()
        total_hits += hits
        total_selected += n_top

    if total_selected == 0:
        return float("nan")
    precision_top20 = total_hits / total_selected
    # Overall positive rate (random baseline)
    overall_rate = y_true.mean()
    if overall_rate < 1e-10:
        return float("nan")
    return float(precision_top20 / overall_rate)


def compute_calibration(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reliability diagram bins.

    Returns (bin_centers, mean_predicted, mean_actual).
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    mean_pred = np.full(n_bins, np.nan)
    mean_actual = np.full(n_bins, np.nan)

    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if mask.sum() >= 5:  # suppress small cells
            mean_pred[i] = y_prob[mask].mean()
            mean_actual[i] = y_true[mask].mean()

    return bin_centers, mean_pred, mean_actual


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------


def bootstrap_logloss_diff(
    y_true: np.ndarray,
    y_prob_m1: np.ndarray,
    y_prob_best: np.ndarray,
    group_idx: np.ndarray,
    n_reps: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Bootstrap CI for ΔlogLoss = logLoss(best) - logLoss(M1).

    Parameters
    ----------
    group_idx : sender_idx or receiver_idx (bootstrap clusters by group)

    Returns
    -------
    delta_mean, ci_lo_95, ci_hi_95
    """
    rng = np.random.default_rng(seed)
    unique_groups = np.unique(group_idx)
    n_groups = len(unique_groups)

    deltas = np.empty(n_reps)
    for b in range(n_reps):
        sampled = rng.choice(unique_groups, size=n_groups, replace=True)
        mask = np.isin(group_idx, sampled)
        # Handle case where sampled groups give zero entries
        if mask.sum() == 0:
            deltas[b] = 0.0
            continue
        ll_m1 = compute_logloss(y_true[mask], y_prob_m1[mask])
        ll_best = compute_logloss(y_true[mask], y_prob_best[mask])
        deltas[b] = ll_best - ll_m1

    delta_mean = float(np.mean(deltas))
    ci_lo = float(np.percentile(deltas, 2.5))
    ci_hi = float(np.percentile(deltas, 97.5))
    return delta_mean, ci_lo, ci_hi


def bootstrap_node_stat(
    values: np.ndarray,
    group_idx: np.ndarray,
    stat_fn: callable,
    n_reps: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Node-level bootstrap for a scalar statistic.

    Returns (point_estimate, ci_lo, ci_hi).
    """
    rng = np.random.default_rng(seed)
    unique_groups = np.unique(group_idx)
    n_groups = len(unique_groups)

    point = float(stat_fn(values))
    boot = np.empty(n_reps)
    for b in range(n_reps):
        sampled = rng.choice(unique_groups, size=n_groups, replace=True)
        mask = np.isin(group_idx, sampled)
        if mask.sum() == 0:
            boot[b] = point
            continue
        boot[b] = float(stat_fn(values[mask]))

    ci_lo = float(np.percentile(boot, 2.5))
    ci_hi = float(np.percentile(boot, 97.5))
    return point, ci_lo, ci_hi


# ---------------------------------------------------------------------------
# Permutation baseline (Z1 test)
# ---------------------------------------------------------------------------


def permutation_baseline_logloss(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_perms: int = 200,
    seed: int = SEED,
) -> tuple[float, float]:
    """Shuffle test labels and compute mean logLoss.

    Returns (mean_perm_logloss, std_perm_logloss).
    Should be ≈ log(2) ≈ 0.693 (random guessing).
    """
    rng = np.random.default_rng(seed)
    losses = []
    for _ in range(n_perms):
        y_perm = rng.permutation(y_true)
        losses.append(compute_logloss(y_perm, y_prob))
    return float(np.mean(losses)), float(np.std(losses))


# ---------------------------------------------------------------------------
# Full evaluation bundle
# ---------------------------------------------------------------------------


def evaluate(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    sender_idx: np.ndarray,
    receiver_idx: np.ndarray,
    y_prob_m1: np.ndarray | None = None,
    label: str = "",
) -> dict:
    """Compute all metrics and return as dict."""
    results: dict = {"label": label}

    results["logloss"] = compute_logloss(y_true, y_prob)
    results["auc"] = compute_auc(y_true, y_prob)
    results["lift_20"] = compute_lift_at_20(y_true, y_prob, sender_idx)

    # Calibration
    bc, mp, ma = compute_calibration(y_true, y_prob)
    results["calibration_bin_centers"] = bc.tolist()
    results["calibration_mean_pred"] = mp.tolist()
    results["calibration_mean_actual"] = ma.tolist()

    if y_prob_m1 is not None:
        # ΔlogLoss vs M1 with bootstrap (sender clustered)
        delta, ci_lo_s, ci_hi_s = bootstrap_logloss_diff(
            y_true, y_prob_m1, y_prob, sender_idx, seed=SEED
        )
        # Second view: receiver clustered
        _, ci_lo_r, ci_hi_r = bootstrap_logloss_diff(
            y_true, y_prob_m1, y_prob, receiver_idx, seed=SEED + 1
        )
        # Conservative: wider CI
        ci_lo = min(ci_lo_s, ci_lo_r)
        ci_hi = max(ci_hi_s, ci_hi_r)
        results["delta_logloss_vs_m1"] = delta
        results["delta_logloss_ci_lo"] = ci_lo
        results["delta_logloss_ci_hi"] = ci_hi

    logger.info(
        "[%s] logLoss=%.4f AUC=%.4f lift@20=%.3f",
        label,
        results["logloss"],
        results["auc"],
        results["lift_20"] if not np.isnan(results["lift_20"]) else -1,
    )
    return results
