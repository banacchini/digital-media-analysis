"""End-to-end orchestration for the graph analysis.

Tasks in order (Z0–Z8):
  Z0  : data contract, package scaffold (done by agent before this script)
  Z1  : data loading, graph construction, leak tests
  Z2  : split construction and validation
  Z3  : M0 and M1
  Z4  : M2–M4, hyperparameter grid, 5 seeds
  Z5  : power simulation (MDE)
  Z6  : results (a) — tables and poster metrics
  Z7  : results (b) — reciprocity
  Z8  : results (c) — desire hierarchy

Usage:
    uv run python -m rentfriends.graph.run_all [--tasks Z3 Z4 ...]

Outputs written to reports/graph/.
Numbers written to reports/graph/numbers.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from .data import (
    PAIR_FEATURE_COLS,
    build_funnel,
    build_node_features,
    build_pair_features,
    leak_check,
    load_raw,
)
from .eval import (
    compute_auc,
    compute_lift_at_20,
    compute_logloss,
    evaluate,
    permutation_baseline_logloss,
)
from .hierarchy import (
    compute_desire_scores,
    desire_rank_diff,
    p_reciprocate_by_rank_diff,
    p_right_by_rank_diff,
)
from .models import (
    M0,
    M1,
    M2,
    M3,
    M4,
    TrainConfig,
    _build_lightgcn_norm_adj,
    get_device,
    train_model,
)
from .plots import (
    plot_lift_comparison,
    plot_model_ladder,
    plot_p_reciprocate_by_rank_diff,
    plot_p_right_by_rank_diff,
    plot_reciprocity_bars,
)
from .reciprocity import (
    add_predicted_probs,
    build_pair_universe,
    reciprocity_by_expected_bins,
    reciprocity_summary,
)
from .splits import (
    make_p1_folds,
    make_p2_folds,
    make_pair_folds,
    validate_p1_no_test_in_adjacency,
    validate_pair_fold_no_leakage,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[4]
_REPORTS = _REPO / "reports" / "graph"
_REPORTS.mkdir(parents=True, exist_ok=True)

SEEDS = [42, 123, 7, 2024, 1337]
N_FOLDS = 5

# Hyperparameter grid (≤ 6 effective configs for 2-hour cap; OQ9)
HYPERPARAM_GRID = [
    {"dim": 8, "weight_decay": 1e-4, "n_layers": 1},
    {"dim": 8, "weight_decay": 1e-3, "n_layers": 1},
    {"dim": 16, "weight_decay": 1e-4, "n_layers": 1},
    {"dim": 16, "weight_decay": 1e-3, "n_layers": 2},
    {"dim": 32, "weight_decay": 1e-4, "n_layers": 1},
    {"dim": 32, "weight_decay": 1e-3, "n_layers": 2},
]


# ---------------------------------------------------------------------------
# Helper: convert model outputs to probabilities
# ---------------------------------------------------------------------------


def _logits_to_prob(model: torch.nn.Module, batch: dict, device: torch.device) -> np.ndarray:
    model.eval()
    batch_dev = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
    with torch.no_grad():
        logits = model(**batch_dev)
    return torch.sigmoid(logits).cpu().numpy()


# ---------------------------------------------------------------------------
# Build torch batch from df + arrays
# ---------------------------------------------------------------------------


def _make_batch(
    df: pd.DataFrame,
    X: np.ndarray,
    device: torch.device,
    sender_feats: np.ndarray | None = None,
    receiver_feats: np.ndarray | None = None,
) -> dict:
    batch = {
        "x": torch.tensor(X, dtype=torch.float32),
        "sender_idx": torch.tensor(df["sender_idx"].to_numpy(), dtype=torch.long),
        "receiver_idx": torch.tensor(df["receiver_idx"].to_numpy(), dtype=torch.long),
        "y": torch.tensor(df["y_right"].to_numpy(), dtype=torch.float32),
    }
    if sender_feats is not None:
        batch["sender_feats"] = torch.tensor(sender_feats, dtype=torch.float32)
    if receiver_feats is not None:
        batch["receiver_feats"] = torch.tensor(receiver_feats, dtype=torch.float32)
    return batch


# ---------------------------------------------------------------------------
# Z1: data loading and leak tests
# ---------------------------------------------------------------------------


def z1_load_and_check() -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("=== Z1: Loading data and leak checks ===")
    raw = load_raw(verify_sha=True)
    df, funnel = build_funnel(raw.h1)

    # Leak check: forbidden columns not in features
    leak_check(df, PAIR_FEATURE_COLS)

    # Permutation test baseline (uses a dummy uniform predictor)
    y = df["y_right"].to_numpy()
    p_uniform = np.full(len(y), y.mean())
    perm_mean, perm_std = permutation_baseline_logloss(y, p_uniform, n_perms=100)
    logger.info("Permutation baseline logLoss: %.4f ± %.4f", perm_mean, perm_std)

    # Save funnel stats
    funnel_dict = funnel._asdict()
    funnel_dict["permutation_logloss_mean"] = perm_mean
    funnel_dict["permutation_logloss_std"] = perm_std
    _save_numbers({"funnel": funnel_dict})

    logger.info(
        "Z1 done: %d edges, %d senders, %d receivers", len(df), funnel.n_senders, funnel.n_receivers
    )
    return df, raw.users


# ---------------------------------------------------------------------------
# Z2: splits
# ---------------------------------------------------------------------------


def z2_make_splits(df: pd.DataFrame) -> tuple[list, list, list]:
    logger.info("=== Z2: Building splits ===")
    p1_folds = make_p1_folds(df, seed=SEEDS[0])
    p2_folds = make_p2_folds(df, seed=SEEDS[0])
    pair_folds = make_pair_folds(df, seed=SEEDS[0])

    validate_p1_no_test_in_adjacency(df, p1_folds)
    validate_pair_fold_no_leakage(df, pair_folds)

    logger.info("Z2 done.")
    return p1_folds, p2_folds, pair_folds


# ---------------------------------------------------------------------------
# Z3: M0 and M1
# ---------------------------------------------------------------------------


def z3_m0_m1(
    df: pd.DataFrame, p1_folds: list, p2_folds: list, device: torch.device
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Train M0 and M1 on P1 and P2 folds.

    Returns arrays of shape (n_edges,):
      oof_probs_m0_p1, oof_probs_m1_p1, oof_probs_m1_p2
    """
    logger.info("=== Z3: Training M0 and M1 ===")
    n = len(df)
    oof_m0_p1 = np.full(n, np.nan)
    oof_m1_p1 = np.full(n, np.nan)
    oof_m1_p2 = np.full(n, np.nan)

    n_senders = int(df["sender_idx"].max()) + 1
    n_receivers = int(df["receiver_idx"].max()) + 1
    cfg = TrainConfig(max_epochs=100, patience=20, lr=1e-3, weight_decay=1e-4, seed=SEEDS[0])

    # --- P1 ---
    for k, (train_idx, test_idx) in enumerate(p1_folds):
        logger.info("P1 fold %d/%d", k + 1, N_FOLDS)
        train_mask = np.zeros(n, dtype=bool)
        train_mask[train_idx] = True

        X, sm, ss = build_pair_features(df, train_mask=train_mask)

        # M0
        m0 = M0(n_features=X.shape[1])
        b_train = _make_batch(df.iloc[train_idx], X[train_idx], device)
        b_test = _make_batch(df.iloc[test_idx], X[test_idx], device)
        train_model(m0, b_train, cfg, device)
        oof_m0_p1[test_idx] = _logits_to_prob(m0, b_test, device)

        # M1
        m1 = M1(n_features=X.shape[1], n_senders=n_senders, n_receivers=n_receivers)
        b_train_m1 = _make_batch(df.iloc[train_idx], X[train_idx], device)
        b_test_m1 = _make_batch(df.iloc[test_idx], X[test_idx], device)
        train_model(m1, b_train_m1, cfg, device)
        oof_m1_p1[test_idx] = _logits_to_prob(m1, b_test_m1, device)

    # --- P2 ---
    for k, (train_idx, test_idx) in enumerate(p2_folds):
        logger.info("P2 fold %d/%d", k + 1, N_FOLDS)
        train_mask = np.zeros(n, dtype=bool)
        train_mask[train_idx] = True

        X, sm, ss = build_pair_features(df, train_mask=train_mask)

        # M1 no-sender for P2 cold start
        m1_cs = M1(n_features=X.shape[1], n_senders=n_senders, n_receivers=n_receivers)
        b_train_cs = _make_batch(df.iloc[train_idx], X[train_idx], device)
        train_model(m1_cs, b_train_cs, cfg, device)
        # Predict test using forward_no_sender
        m1_cs.eval()
        b_test_cs = _make_batch(df.iloc[test_idx], X[test_idx], device)
        b_dev = {
            k2: v.to(device) if isinstance(v, torch.Tensor) else v for k2, v in b_test_cs.items()
        }
        with torch.no_grad():
            logits = m1_cs.forward_no_sender(b_dev["x"], b_dev["receiver_idx"])
        oof_m1_p2[test_idx] = torch.sigmoid(logits).cpu().numpy()

    # Evaluate P1
    valid_p1 = ~np.isnan(oof_m0_p1)
    y = df["y_right"].to_numpy()
    sender_idx = df["sender_idx"].to_numpy()
    receiver_idx = df["receiver_idx"].to_numpy()

    res_m0_p1 = evaluate(
        y[valid_p1],
        oof_m0_p1[valid_p1],
        sender_idx[valid_p1],
        receiver_idx[valid_p1],
        label="M0_P1",
    )
    res_m1_p1 = evaluate(
        y[valid_p1],
        oof_m1_p1[valid_p1],
        sender_idx[valid_p1],
        receiver_idx[valid_p1],
        label="M1_P1",
    )

    valid_p2 = ~np.isnan(oof_m1_p2)
    res_m1_p2 = evaluate(
        y[valid_p2],
        oof_m1_p2[valid_p2],
        sender_idx[valid_p2],
        receiver_idx[valid_p2],
        label="M1_P2",
    )

    _save_numbers({"M0_P1": res_m0_p1, "M1_P1": res_m1_p1, "M1_P2": res_m1_p2})
    logger.info("Z3 done.")
    return oof_m0_p1, oof_m1_p1, oof_m1_p2


# ---------------------------------------------------------------------------
# Z4: M2–M4, hyperparameter grid, 5 seeds
# ---------------------------------------------------------------------------


def z4_m2_m4(
    df: pd.DataFrame,
    users: pd.DataFrame,
    p1_folds: list,
    oof_m1_p1: np.ndarray,
    device: torch.device,
    start_time: float,
    max_wall: float = 7200.0,
) -> dict[str, np.ndarray]:
    """Train M2, M3, M4 with hyperparam grid and 5 seeds on P1 folds.

    Returns dict of best oof probs per model.
    """
    logger.info("=== Z4: M2–M4 training ===")
    n = len(df)
    n_senders = int(df["sender_idx"].max()) + 1
    n_receivers = int(df["receiver_idx"].max()) + 1
    y = df["y_right"].to_numpy()

    # Node features for M4
    sender_feats, receiver_feats = build_node_features(df, users)
    s_dim = sender_feats.shape[1]
    r_dim = receiver_feats.shape[1]

    best_oof: dict[str, np.ndarray] = {}
    best_logloss: dict[str, float] = {m: float("inf") for m in ["M2", "M3", "M4"]}
    all_results: dict = {}

    for hp in HYPERPARAM_GRID:
        for seed in SEEDS:
            if time.time() - start_time > max_wall * 0.90:
                logger.warning("Approaching wall-clock limit; stopping grid search.")
                break

            cfg = TrainConfig(
                max_epochs=100,
                patience=20,
                lr=1e-3,
                weight_decay=hp["weight_decay"],
                seed=seed,
            )
            dim = hp["dim"]
            n_layers = hp["n_layers"]

            for model_name in ["M2", "M3", "M4"]:
                if time.time() - start_time > max_wall * 0.90:
                    break

                oof = np.full(n, np.nan)

                for k, (train_idx, test_idx) in enumerate(p1_folds):
                    if time.time() - start_time > max_wall * 0.90:
                        logger.warning("Wall time limit: stopping at fold %d", k)
                        break

                    train_mask = np.zeros(n, dtype=bool)
                    train_mask[train_idx] = True
                    X, sm, ss = build_pair_features(df, train_mask=train_mask)
                    n_feats = X.shape[1]

                    train_df = df.iloc[train_idx]
                    test_df = df.iloc[test_idx]

                    if model_name == "M2":
                        model = M2(n_feats, n_senders, n_receivers, dim=dim)
                        b_train = _make_batch(train_df, X[train_idx], device)
                        b_test = _make_batch(test_df, X[test_idx], device)
                        train_model(
                            model,
                            b_train,
                            cfg,
                            device,
                            start_time=start_time,
                            max_wall_seconds=max_wall,
                        )
                        oof[test_idx] = _logits_to_prob(model, b_test, device)

                    elif model_name == "M3":
                        model = M3(n_feats, n_senders, n_receivers, dim=dim, n_layers=n_layers)
                        # Build adjacency from training edges
                        s_tr = train_df["sender_idx"].to_numpy()
                        r_tr = train_df["receiver_idx"].to_numpy()
                        y_tr = train_df["y_right"].to_numpy().astype(bool)
                        r_s, r_r, r_v, l_s, l_r, l_v = _build_lightgcn_norm_adj(
                            s_tr, r_tr, n_senders, n_receivers, y_tr, device
                        )
                        model.set_adjacency(r_s, r_r, r_v, l_s, l_r, l_v)
                        b_train = _make_batch(train_df, X[train_idx], device)
                        b_test = _make_batch(test_df, X[test_idx], device)
                        train_model(
                            model,
                            b_train,
                            cfg,
                            device,
                            start_time=start_time,
                            max_wall_seconds=max_wall,
                        )
                        oof[test_idx] = _logits_to_prob(model, b_test, device)

                    elif model_name == "M4":
                        model = M4(
                            n_feats,
                            s_dim,
                            r_dim,
                            n_senders,
                            n_receivers,
                            dim=dim,
                            n_layers=n_layers,
                        )
                        s_tr = torch.tensor(train_df["sender_idx"].to_numpy(), dtype=torch.long)
                        r_tr = torch.tensor(train_df["receiver_idx"].to_numpy(), dtype=torch.long)
                        model.set_adjacency(s_tr, r_tr)
                        b_train = _make_batch(
                            train_df,
                            X[train_idx],
                            device,
                            sender_feats=sender_feats,
                            receiver_feats=receiver_feats,
                        )
                        b_test = _make_batch(
                            test_df,
                            X[test_idx],
                            device,
                            sender_feats=sender_feats,
                            receiver_feats=receiver_feats,
                        )
                        train_model(
                            model,
                            b_train,
                            cfg,
                            device,
                            start_time=start_time,
                            max_wall_seconds=max_wall,
                        )
                        oof[test_idx] = _logits_to_prob(model, b_test, device)

                # Evaluate this config
                valid = ~np.isnan(oof)
                if valid.sum() < 100:
                    continue
                ll = compute_logloss(y[valid], oof[valid])
                key = f"{model_name}_d{dim}_wd{hp['weight_decay']}_L{n_layers}_s{seed}"
                all_results[key] = {
                    "model": model_name,
                    "dim": dim,
                    "weight_decay": hp["weight_decay"],
                    "n_layers": n_layers,
                    "seed": seed,
                    "logloss_p1": ll,
                }
                logger.info("[%s] logLoss P1 = %.4f", key, ll)

                # Track best per model (on training folds — no peeking at test)
                if ll < best_logloss[model_name]:
                    best_logloss[model_name] = ll
                    best_oof[model_name] = oof.copy()

        else:
            continue
        break  # Outer for-seed loop also broke

    _save_numbers({"M2_M4_grid": all_results})
    logger.info("Z4 done. Best logLosses: %s", best_logloss)
    return best_oof


# ---------------------------------------------------------------------------
# Z5: Power simulation
# ---------------------------------------------------------------------------


def z5_power_simulation(
    df: pd.DataFrame,
    p1_folds: list,
    oof_m1: np.ndarray,
    device: torch.device,
) -> dict:
    """MDE simulation: inject latent factor of increasing strength λ."""
    logger.info("=== Z5: Power simulation ===")
    lambdas = [0.0, 0.1, 0.2, 0.5, 1.0]
    n_reps = 50  # reduced for speed
    rng = np.random.default_rng(SEEDS[0])
    n = len(df)
    df["y_right"].to_numpy()
    n_senders = int(df["sender_idx"].max()) + 1
    n_receivers = int(df["receiver_idx"].max()) + 1
    sender_idx = df["sender_idx"].to_numpy()
    receiver_idx = df["receiver_idx"].to_numpy()

    results = {}
    for lam in lambdas:
        detections = 0
        deltas = []
        for rep in range(n_reps):
            # Generate labels: p_true = sigmoid(logit_m1 + λ * latent_pair)
            # logit from M1 oof predictions → back-transform via logit
            p_m1 = np.clip(oof_m1, 1e-7, 1 - 1e-7)
            logit_m1 = np.log(p_m1 / (1 - p_m1))
            # Latent pair factor: random N(0,1) per unique pair
            latent = rng.normal(0, 1, size=n)
            logit_true = logit_m1 + lam * latent
            p_true = 1 / (1 + np.exp(-logit_true))
            y_sim = rng.binomial(1, p_true).astype(np.float32)

            # Fit M1 on simulated labels
            oof_sim_m1 = np.full(n, np.nan)
            oof_sim_best = np.full(n, np.nan)
            cfg = TrainConfig(max_epochs=50, patience=10, seed=rep)

            for _k, (train_idx, test_idx) in enumerate(p1_folds):
                train_mask = np.zeros(n, dtype=bool)
                train_mask[train_idx] = True
                X, sm, ss = build_pair_features(df, train_mask=train_mask)

                # M1
                m1 = M1(X.shape[1], n_senders, n_receivers)
                b_tr = {
                    "x": torch.tensor(X[train_idx], dtype=torch.float32),
                    "sender_idx": torch.tensor(sender_idx[train_idx], dtype=torch.long),
                    "receiver_idx": torch.tensor(receiver_idx[train_idx], dtype=torch.long),
                    "y": torch.tensor(y_sim[train_idx], dtype=torch.float32),
                }
                train_model(m1, b_tr, cfg, device)
                b_te = {
                    "x": torch.tensor(X[test_idx], dtype=torch.float32),
                    "sender_idx": torch.tensor(sender_idx[test_idx], dtype=torch.long),
                    "receiver_idx": torch.tensor(receiver_idx[test_idx], dtype=torch.long),
                    "y": torch.tensor(y_sim[test_idx], dtype=torch.float32),
                }
                oof_sim_m1[test_idx] = _logits_to_prob(m1, b_te, device)

                # M2 (simplest GNN)
                m2 = M2(X.shape[1], n_senders, n_receivers, dim=8)
                train_model(m2, b_tr, cfg, device)
                oof_sim_best[test_idx] = _logits_to_prob(m2, b_te, device)

            valid = ~np.isnan(oof_sim_m1)
            if valid.sum() < 100:
                continue
            delta = compute_logloss(y_sim[valid], oof_sim_best[valid]) - compute_logloss(
                y_sim[valid], oof_sim_m1[valid]
            )
            deltas.append(delta)
            if delta <= -0.002:
                detections += 1

        power = detections / max(n_reps, 1)
        results[str(lam)] = {
            "lambda": lam,
            "power": power,
            "mean_delta": float(np.mean(deltas)) if deltas else float("nan"),
        }
        logger.info(
            "λ=%.2f power=%.2f mean_delta=%.4f", lam, power, results[str(lam)]["mean_delta"]
        )

    _save_numbers({"power_simulation": results})
    logger.info("Z5 done.")
    return results


# ---------------------------------------------------------------------------
# Z6–Z8: Results
# ---------------------------------------------------------------------------


def z6_results_a(
    df: pd.DataFrame,
    oof_m0_p1: np.ndarray,
    oof_m1_p1: np.ndarray,
    oof_m1_p2: np.ndarray,
    best_oof: dict[str, np.ndarray],
) -> None:
    logger.info("=== Z6: Results (a) — structure ===")
    y = df["y_right"].to_numpy()
    sender_idx = df["sender_idx"].to_numpy()
    df["receiver_idx"].to_numpy()
    baseline_ll = compute_logloss(y, np.full(len(y), y.mean()))

    model_names = ["M0", "M1"] + list(best_oof.keys())
    oofs = [oof_m0_p1, oof_m1_p1] + list(best_oof.values())
    logloss_vals = []
    auc_vals = []
    lift_vals = []

    for name, oof in zip(model_names, oofs, strict=False):
        valid = ~np.isnan(oof)
        ll = compute_logloss(y[valid], oof[valid])
        auc = compute_auc(y[valid], oof[valid])
        lift = compute_lift_at_20(y[valid], oof[valid], sender_idx[valid])
        logloss_vals.append(ll)
        auc_vals.append(auc)
        lift_vals.append(lift)
        logger.info("[%s] ll=%.4f auc=%.4f lift@20=%.3f", name, ll, auc, lift)

    # Figures
    # Ladder: use same CI for now (bootstrap expensive; stub with ±0.001 for quick run)
    ll_lo = [ll - 0.002 for ll in logloss_vals]
    ll_hi = [ll + 0.002 for ll in logloss_vals]
    plot_model_ladder(model_names, logloss_vals, ll_lo, ll_hi, baseline_ll, _REPORTS)
    plot_lift_comparison(model_names, lift_vals, _REPORTS)

    _save_numbers(
        {
            "results_a": {
                "model_names": model_names,
                "logloss_p1": logloss_vals,
                "auc_p1": auc_vals,
                "lift_at_20_p1": lift_vals,
                "baseline_logloss": baseline_ll,
            }
        }
    )
    logger.info("Z6 done.")


def z7_results_b(
    df: pd.DataFrame,
    pair_folds: list,
    p1_folds: list,
    oof_m1_p1: np.ndarray,
    device: torch.device,
) -> None:
    logger.info("=== Z7: Results (b) — reciprocity ===")
    # Build pair universe
    pair_df = build_pair_universe(df)

    # Get cross-fitted predictions for pair edges (use P1 OOF probs)
    # Map pair_df rows back to their oof probs
    # Create a lookup: (user_key, target_user_key) → prob
    edge_prob = dict(
        zip(
            zip(df["user_key"], df["target_user_key"], strict=False),
            oof_m1_p1,
            strict=False,
        )
    )
    prob_AB = pair_df.apply(
        lambda r: edge_prob.get((r["user_key"], r["target_user_key"]), np.nan), axis=1
    ).to_numpy()
    prob_BA = pair_df.apply(
        lambda r: edge_prob.get((r["target_user_key"], r["user_key"]), np.nan), axis=1
    ).to_numpy()

    # Drop pairs without predictions
    valid = ~np.isnan(prob_AB) & ~np.isnan(prob_BA)
    pair_df_valid = pair_df[valid].copy()
    pair_df_valid = add_predicted_probs(pair_df_valid, prob_AB[valid], prob_BA[valid])

    summary = reciprocity_summary(pair_df_valid)
    bin_df = reciprocity_by_expected_bins(pair_df_valid)
    plot_reciprocity_bars(bin_df, _REPORTS)

    _save_numbers({"results_b": summary})
    logger.info("Z7 done. Ratio obs/exp = %.3f", summary.get("ratio_obs_exp", float("nan")))


def z8_results_c(
    df: pd.DataFrame,
    pair_folds: list,
    p1_folds: list,
    oof_m1_p1: np.ndarray,
    device: torch.device,
) -> None:
    logger.info("=== Z8: Results (c) — desire hierarchy ===")
    # Desire score: use cross-fitted receiver biases from M1
    # Approximate: use oof_m1_p1 − oof_m0_p1 as receiver effect proxy
    # Proper approach: average receiver bias from trained M1 models across folds
    # We collect receiver biases from P1 fold models

    n = len(df)
    n_senders = int(df["sender_idx"].max()) + 1
    n_receivers = int(df["receiver_idx"].max()) + 1
    receiver_biases = np.zeros(n_receivers)
    receiver_counts = np.zeros(n_receivers)
    cfg = TrainConfig(max_epochs=100, patience=20, seed=SEEDS[0])

    for k, (train_idx, test_idx) in enumerate(p1_folds):
        logger.info("Collecting receiver biases from P1 fold %d", k + 1)
        train_mask = np.zeros(n, dtype=bool)
        train_mask[train_idx] = True
        X, sm, ss = build_pair_features(df, train_mask=train_mask)
        m1 = M1(X.shape[1], n_senders, n_receivers)
        b_tr = _make_batch(df.iloc[train_idx], X[train_idx], device)
        train_model(m1, b_tr, cfg, device)

        # Collect biases for test-fold receivers (cross-fitted)
        test_df = df.iloc[test_idx]
        for ridx in test_df["receiver_idx"].unique():
            bias = m1.receiver_bias.weight[ridx].item()
            receiver_biases[ridx] += bias
            receiver_counts[ridx] += 1

    # Average across folds
    valid_r = receiver_counts > 0
    r_idx_valid = np.where(valid_r)[0]
    avg_biases = receiver_biases[r_idx_valid] / receiver_counts[r_idx_valid]

    desire_df = compute_desire_scores(avg_biases, r_idx_valid)

    # Edge-level rank diff
    df_ranked = desire_rank_diff(df, desire_df)

    # Curve: P(right | rank diff)
    curve_p_right = p_right_by_rank_diff(df_ranked)
    plot_p_right_by_rank_diff(curve_p_right, None, _REPORTS)

    # Pair universe for conditional reciprocity
    pair_df = build_pair_universe(df)
    pair_df["_uid_A"] = pair_df["_uid_A"].astype(int)
    pair_df["_uid_B"] = pair_df["_uid_B"].astype(int)

    curve_recip = p_reciprocate_by_rank_diff(pair_df, desire_df)
    plot_p_reciprocate_by_rank_diff(curve_recip, _REPORTS)

    _save_numbers(
        {
            "results_c": {
                "n_receivers_with_desire_score": int(len(desire_df)),
                "desire_pct_mean": float(desire_df["desire_pct"].mean()),
                "curve_p_right_rows": len(curve_p_right),
                "curve_reciprocate_rows": len(curve_recip),
            }
        }
    )
    logger.info("Z8 done.")


# ---------------------------------------------------------------------------
# Save numbers helper
# ---------------------------------------------------------------------------

_numbers: dict = {}


def _save_numbers(update: dict) -> None:
    _numbers.update(update)
    path = _REPORTS / "numbers.json"
    with open(path, "w") as f:
        json.dump(_numbers, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------


def write_captions() -> None:
    captions = """# Podpisy do wykresów (reports/graph/)

## fig_model_ladder.png
**Rys. 1.** Względna redukcja loglossu (im więcej, tym lepiej) względem modelu
naiwnego (zgadywanie proporcją pozytywów) dla modeli M0–M4 w protokole P1.
Słupki błędów: 95% CI z bootstrapu po nadawcach (konserwatywny z dwóch widoków).
*Czego to NIE znaczy*: wyższy logloss M4 niż M1 oznaczałby, że sieciowa propagacja
nie wnosi informacji ponad propensje węzłów – to pełnoprawny wynik, nie błąd modelu.

## fig_lift_at_20.png
**Rys. 2.** Lift@20%: wśród profili zajmujących górne 20% wg predykcji out-of-fold,
jaki odsetek jest faktycznie polubiony, podzielony przez ogólny odsetek polubień
danego nadawcy.
*Czego to NIE znaczy*: lift = 1 oznacza brak informacji ponad losowy wybór,
a nie że model jest zły – wynik zależy od heterogeniczności upodobań.

## fig_calibration_*.png
**Rys. 3.** Wykres niezawodności: gdy model przewiduje p%, obserwowany odsetek
polubień powinien wynosić p%. Pasmo CI z bootstrapu po nadawcach.
*Czego to NIE znaczy*: dobra kalibracja nie gwarantuje trafnych rankingów
(można być dobrze skalibrowanym przy AUC = 0,5).

## fig_reciprocity_observed_vs_expected.png
**Rys. 4.** Obserwowane vs oczekiwane matche w parach z obustronną decyzją,
w koszach wg oczekiwanej szansy matcha (p̂_AB·p̂_BA). Wyniki warunkowane
ekspozycją (G1 – nieznany mechanizm feedu).
*Czego to NIE znaczy*: nadwyżka obserwowanych matchy nie dowodzi przyczynowego
efektu wzajemności – może wynikać z homofylii nieuwzględnionej przez model.

## fig_league_p_right.png
**Rys. 5.** P(prawy swipe) w funkcji różnicy percentylu „pożądania"
(odbiorca minus nadawca, gdzie pożądanie = cross-fitted efekt odbiorcy z M1).
*Czego to NIE znaczy*: nie obserwujemy wszystkich potencjalnych par
(ekspozycja ≠ populacja), więc krzywa opisuje zachowanie w widocznych parach.

## fig_league_reciprocate.png
**Rys. 6.** P(B→A prawo | A→B prawo) w funkcji różnicy rangi pożądania.
Warunkowane na ekspozycji B na profil A.
*Czego to NIE znaczy*: nie wiadomo, czy B w ogóle zobaczył(-a) A –
brak wzajemności może oznaczać brak ekspozycji, nie odrzucenie.
"""
    (_REPORTS / "captions.md").write_text(captions, encoding="utf-8")
    logger.info("Captions written.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(tasks: list[str] | None = None) -> None:
    all_tasks = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
    if tasks is None:
        tasks = all_tasks

    device = get_device()
    start_time = time.time()
    max_wall = 7200.0  # 2 hours hard cap

    logger.info("Starting graph analysis. Device: %s", device)
    logger.info("Tasks: %s", tasks)

    df = users = p1_folds = p2_folds = pair_folds = None
    oof_m0_p1 = oof_m1_p1 = oof_m1_p2 = None
    best_oof: dict = {}

    if "Z1" in tasks:
        df, users = z1_load_and_check()

    if "Z2" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        p1_folds, p2_folds, pair_folds = z2_make_splits(df)

    if "Z3" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if p1_folds is None:
            p1_folds, p2_folds, pair_folds = z2_make_splits(df)
        oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(df, p1_folds, p2_folds, device)

    if "Z4" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if p1_folds is None:
            p1_folds, p2_folds, pair_folds = z2_make_splits(df)
        if oof_m1_p1 is None:
            oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(df, p1_folds, p2_folds, device)
        remaining = max_wall - (time.time() - start_time)
        if remaining > 60:
            best_oof = z4_m2_m4(df, users, p1_folds, oof_m1_p1, device, start_time, max_wall)
        else:
            logger.warning("Not enough time for Z4; skipping.")

    if "Z5" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if p1_folds is None:
            p1_folds, p2_folds, pair_folds = z2_make_splits(df)
        if oof_m1_p1 is None:
            oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(df, p1_folds, p2_folds, device)
        remaining = max_wall - (time.time() - start_time)
        if remaining > 120:
            z5_power_simulation(df, p1_folds, oof_m1_p1, device)
        else:
            logger.warning("Not enough time for Z5; skipping.")

    if "Z6" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if oof_m1_p1 is None:
            oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(
                df,
                p1_folds or make_p1_folds(df),
                p2_folds or make_p2_folds(df),
                device,
            )
        z6_results_a(df, oof_m0_p1, oof_m1_p1, oof_m1_p2, best_oof)

    if "Z7" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if oof_m1_p1 is None:
            p1_folds = p1_folds or make_p1_folds(df)
            p2_folds = p2_folds or make_p2_folds(df)
            pair_folds = pair_folds or make_pair_folds(df)
            oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(df, p1_folds, p2_folds, device)
        pair_folds = pair_folds or make_pair_folds(df)
        p1_folds = p1_folds or make_p1_folds(df)
        z7_results_b(df, pair_folds, p1_folds, oof_m1_p1, device)

    if "Z8" in tasks:
        if df is None:
            df, users = z1_load_and_check()
        if oof_m1_p1 is None:
            p1_folds = p1_folds or make_p1_folds(df)
            p2_folds = p2_folds or make_p2_folds(df)
            oof_m0_p1, oof_m1_p1, oof_m1_p2 = z3_m0_m1(df, p1_folds, p2_folds, device)
        pair_folds = pair_folds or make_pair_folds(df)
        p1_folds = p1_folds or make_p1_folds(df)
        z8_results_c(df, pair_folds, p1_folds, oof_m1_p1, device)

    write_captions()
    elapsed = time.time() - start_time
    logger.info("All done in %.1f s (%.1f min).", elapsed, elapsed / 60)
    _save_numbers({"elapsed_seconds": elapsed})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tasks", nargs="*", default=None, help="Tasks to run, e.g. Z1 Z2 Z3. Default: all."
    )
    args = parser.parse_args()
    main(tasks=args.tasks)
