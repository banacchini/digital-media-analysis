"""Data loading, SHA-256 verification, feature engineering, and sample funnel.

Hard rules (from graph-stream-prompt.md):
- h1_analysis_dataset.parquet is read-only; SHA-256 verified at load time.
- Forbidden columns (leakage): sender_right_rate, sender_total_swipes,
  is_extreme_user, is_low_activity, match.
- bio column is NEVER read or used.
- user_key never appears in output files or figures.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths (relative to repo root; resolve at call time)
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parents[3]
_H1_PATH = _REPO / "data" / "processed" / "h1_analysis_dataset.parquet"
_SWIPES_PATH = _REPO / "data" / "processed" / "swipes.parquet"
_USERS_PATH = _REPO / "data" / "processed" / "users.parquet"

H1_SHA256 = "1f0bb5b1e02e968772931b341655405b09a81f257ca90d3ff9f5862186d3f771"

# ---------------------------------------------------------------------------
# Forbidden columns (leakage)
# ---------------------------------------------------------------------------
FORBIDDEN_COLS = frozenset(
    ["sender_right_rate", "sender_total_swipes", "is_extreme_user", "is_low_activity", "match"]
)

# ---------------------------------------------------------------------------
# Pair feature columns (from frozen parquet, used as model input)
# ---------------------------------------------------------------------------
PAIR_FEATURE_COLS = [
    "sex_pair",
    "same_band",
    "age_band_diff",
    "age_band_diff_abs",
    "city_same",
    "city_diff",
    "interests_jaccard",
    "interests_shared_n",
    "lifestyle_agree_ratio",
    "lifestyle_tag_conflict",
    "lifestyle_shared_tags_n",
]

# Sex-pair categories (for one-hot encoding)
SEX_PAIR_CATEGORIES = ["M→M", "M→F", "M→O", "F→M", "F→F", "F→O", "O→M", "O→F", "O→O"]


# ---------------------------------------------------------------------------
# SHA-256 verification
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_h1_sha256() -> None:
    """Raise RuntimeError if h1_analysis_dataset.parquet has changed."""
    actual = _sha256(_H1_PATH)
    if actual != H1_SHA256:
        raise RuntimeError(
            f"h1_analysis_dataset.parquet SHA-256 mismatch!\n"
            f"  expected: {H1_SHA256}\n"
            f"  actual  : {actual}\n"
            "The frozen dataset has changed. Update data-contract.md if intentional."
        )
    logger.info("SHA-256 verified: h1_analysis_dataset.parquet OK")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


class RawData(NamedTuple):
    h1: pd.DataFrame
    users: pd.DataFrame


def load_raw(verify_sha: bool = True) -> RawData:
    """Load h1 and users; optionally verify SHA-256 of h1."""
    if verify_sha:
        verify_h1_sha256()

    h1 = pd.read_parquet(_H1_PATH)
    # Safety: drop bio if somehow present (it shouldn't be in h1, but be safe)
    h1 = h1.drop(columns=["bio"], errors="ignore")
    # Assert no forbidden columns used as features (they may still be present in the df)
    logger.debug("h1 shape: %s", h1.shape)

    users = pd.read_parquet(_USERS_PATH)
    # Drop bio immediately
    users = users.drop(columns=["bio"], errors="ignore")
    logger.debug("users shape: %s", users.shape)

    return RawData(h1=h1, users=users)


# ---------------------------------------------------------------------------
# Sample funnel
# ---------------------------------------------------------------------------


class FunnelStats(NamedTuple):
    h1_rows: int
    after_complete_case: int
    n_senders: int
    n_receivers: int
    n_right: int
    n_left: int
    n_pairs_both: int
    n_matches_reconstructed: int


def build_funnel(h1: pd.DataFrame) -> tuple[pd.DataFrame, FunnelStats]:
    """Apply complete-case filter on pair features and return funnel stats.

    Note: h1 already has Hyderabad filtered out by the H1 pipeline.
    """
    df = h1.copy()
    h1_rows = len(df)

    # city_same and city_diff from same_city (which has values 'same', 'different', 'unknown')
    if "city_same" not in df.columns:
        df["city_same"] = (df["same_city"] == "same").astype(np.float32)
    if "city_diff" not in df.columns:
        df["city_diff"] = (df["same_city"] == "different").astype(np.float32)

    # Complete-case: drop rows where any PAIR_FEATURE_COLS have NaN
    # (sex_pair, same_band, city_same, city_diff are always present; others may be NaN)
    numeric_pair_cols = [c for c in PAIR_FEATURE_COLS if c not in ("sex_pair",) and c in df.columns]
    before_cc = len(df)
    df = df.dropna(subset=numeric_pair_cols).reset_index(drop=True)
    after_cc = len(df)
    if before_cc != after_cc:
        logger.info("Complete-case filter: %d → %d rows", before_cc, after_cc)

    # Build integer node IDs for bipartite graph
    # senders and receivers are separate node sets
    sender_ids = pd.Categorical(df["user_key"])
    receiver_ids = pd.Categorical(df["target_user_key"])
    df["sender_idx"] = sender_ids.codes
    df["receiver_idx"] = receiver_ids.codes
    df["sender_uid"] = sender_ids.codes  # internal; user_key never exported
    df["receiver_uid"] = receiver_ids.codes

    n_senders = df["sender_idx"].nunique()
    n_receivers = df["receiver_idx"].nunique()
    n_right = int(df["y_right"].sum())
    n_left = len(df) - n_right

    # Reciprocal pairs (both A→B and B→A present)
    pair_A = df[["user_key", "target_user_key", "y_right"]].copy()
    pair_B = df[["user_key", "target_user_key", "y_right"]].rename(
        columns={
            "user_key": "target_user_key",
            "target_user_key": "user_key",
            "y_right": "y_right_B",
        }
    )
    both = pair_A.merge(pair_B, on=["user_key", "target_user_key"])
    n_pairs_both = len(both) // 2  # unordered pairs
    n_matches_reconstructed = int((both["y_right"] & both["y_right_B"]).sum()) // 2

    stats = FunnelStats(
        h1_rows=h1_rows,
        after_complete_case=after_cc,
        n_senders=n_senders,
        n_receivers=n_receivers,
        n_right=n_right,
        n_left=n_left,
        n_pairs_both=n_pairs_both,
        n_matches_reconstructed=n_matches_reconstructed,
    )
    logger.info("Funnel: %s", stats)
    return df, stats


# ---------------------------------------------------------------------------
# Feature matrix construction
# ---------------------------------------------------------------------------


def build_pair_features(
    df: pd.DataFrame,
    train_mask: np.ndarray | None = None,
    *,
    scaler_mean: np.ndarray | None = None,
    scaler_std: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Build the pair-feature matrix X from df.

    Parameters
    ----------
    df          : graph dataframe (output of build_funnel)
    train_mask  : boolean mask for training rows (used to fit scaler)
    scaler_mean : pre-fitted mean (use on test folds)
    scaler_std  : pre-fitted std  (use on test folds)

    Returns
    -------
    X, scaler_mean, scaler_std
    """
    # Verify no forbidden columns are being used
    assert not FORBIDDEN_COLS.intersection(PAIR_FEATURE_COLS), "Leakage in feature list!"

    parts = []

    # sex_pair → one-hot
    if "sex_pair" in df.columns:
        dummies = pd.get_dummies(df["sex_pair"], prefix="sex").reindex(
            columns=[f"sex_{c}" for c in SEX_PAIR_CATEGORIES], fill_value=0
        )
        parts.append(dummies.values.astype(np.float32))

    # Ensure city_same and city_diff exist
    if "city_same" not in df.columns and "same_city" in df.columns:
        df = df.copy()
        df["city_same"] = (df["same_city"] == "same").astype(np.float32)
    if "city_diff" not in df.columns and "same_city" in df.columns:
        df = df.copy()
        df["city_diff"] = (df["same_city"] == "different").astype(np.float32)

    # Numeric pair features (with missing indicators)
    numeric_cols = [
        "same_band",
        "age_band_diff",
        "age_band_diff_abs",
        "city_same",
        "city_diff",
        "interests_jaccard",
        "interests_shared_n",
        "lifestyle_agree_ratio",
        "lifestyle_tag_conflict",
        "lifestyle_shared_tags_n",
    ]
    for col in numeric_cols:
        if col in df.columns:
            vals = df[col].to_numpy(dtype=np.float32)
            missing = np.isnan(vals).astype(np.float32)
            vals = np.where(np.isnan(vals), 0.0, vals)
            parts.append(vals.reshape(-1, 1))
            if missing.any():
                parts.append(missing.reshape(-1, 1))

    X = np.hstack(parts) if parts else np.zeros((len(df), 0), dtype=np.float32)

    # Standardise numeric columns (not one-hot, not binary indicators)
    # We standardise all columns except the sex one-hot (first 9) and binary flags
    # Simple approach: standardise everything with train stats
    if train_mask is not None:
        X_train = X[train_mask]
        scaler_mean = X_train.mean(axis=0)
        scaler_std = X_train.std(axis=0)
        scaler_std = np.where(scaler_std < 1e-8, 1.0, scaler_std)

    if scaler_mean is not None and scaler_std is not None:
        X = (X - scaler_mean) / scaler_std

    return X, scaler_mean, scaler_std


def build_node_features(df: pd.DataFrame, users: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build node feature matrices for senders and receivers (M4).

    Returns
    -------
    sender_feats  : array of shape (n_senders, n_node_feats)
    receiver_feats: array of shape (n_receivers, n_node_feats)
    """
    # Static profile features (not label-derived)
    feat_cols = ["sex", "age_band", "city"]
    # Build a lookup: user_key → feature vector
    users_sub = users[["user_key"] + feat_cols].copy()

    # One-hot encode categorical columns
    users_encoded = pd.get_dummies(users_sub, columns=feat_cols, dummy_na=False)
    users_encoded = users_encoded.set_index("user_key")

    # Map senders
    sender_map = df[["user_key", "sender_idx"]].drop_duplicates().set_index("user_key")
    n_senders = df["sender_idx"].max() + 1
    sender_feats = np.zeros((n_senders, users_encoded.shape[1]), dtype=np.float32)
    for uk, row in sender_map.iterrows():
        if uk in users_encoded.index:
            sender_feats[int(row["sender_idx"])] = users_encoded.loc[uk].values.astype(np.float32)

    # Map receivers
    receiver_map = (
        df[["target_user_key", "receiver_idx"]].drop_duplicates().set_index("target_user_key")
    )
    n_receivers = df["receiver_idx"].max() + 1
    receiver_feats = np.zeros((n_receivers, users_encoded.shape[1]), dtype=np.float32)
    for uk, row in receiver_map.iterrows():
        if uk in users_encoded.index:
            receiver_feats[int(row["receiver_idx"])] = users_encoded.loc[uk].values.astype(
                np.float32
            )

    return sender_feats, receiver_feats


def leak_check(df: pd.DataFrame, feature_cols: list[str]) -> None:
    """Assert that no forbidden (leaky) columns are in feature_cols."""
    leaky = FORBIDDEN_COLS.intersection(feature_cols)
    if leaky:
        raise ValueError(f"Leakage detected! Forbidden columns in features: {leaky}")
    logger.info("Leak check passed: no forbidden columns in features.")
