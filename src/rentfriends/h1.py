"""H1: Lifestyle compatibility versus age and interests in predicting roommate acceptance.

Implements the empirical test of Hypothesis H1:
- Unit: directed swipe A -> B on a profile, outcome `y_right`.
- Features strictly limited to H1 construct: lifestyle, interests, age, sex baseline,
  and same_city control.
- Nested block model comparisons:
  - Baseline/Comparison block: Age and Interests (+ demographic baseline controls).
  - Target block: Lifestyle compatibility.
  - Evaluation of both inclusion orders (D16).
- Two-way clustered standard errors on sender and receiver (D18).
- Shuffled null baseline via receiver lifestyle permutation.
- Out-of-sample evaluation via user-grouped 5-fold cross-validation.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, rankdata

from rentfriends.dataset_h1 import build_h1_dataset

# Style constants matching STYLEGUIDE.md
PURPLE = "#A247E3"
PURPLE_INK = "#8B34C4"
BLUE = "#234CE0"
GRAY = "#595959"
HAIR = "#D5D2CB"
CORAL = "#D9534F"

# Feature definitions for H1 blocks
DEMOG_COLS = ["same_band", "age_band_diff", "same_sex"]
INTERESTS_COLS = ["interests_jaccard", "interests_shared_n", "interests_count_diff_abs"]
LIFESTYLE_COLS = ["lifestyle_agree_ratio", "lifestyle_tag_conflict", "lifestyle_shared_tags_n"]
CONTROL_COLS = ["city_same", "city_diff"]


def load_h1_data(data_dir: Path | str = "data/processed") -> pd.DataFrame:
    """Load or generate the clean H1 dataset."""
    data_path = Path(data_dir)
    file_path = data_path / "h1_analysis_dataset.parquet"
    if file_path.exists():
        df = pd.read_parquet(file_path)
    else:
        df = build_h1_dataset(data_dir=data_path, docs_dir="docs")
        df.to_parquet(file_path, index=False)

    # Prepare city dummy columns
    df["city_same"] = (df["same_city"] == "same").astype(float)
    df["city_diff"] = (df["same_city"] == "different").astype(float)
    return df


def wilson_interval(k: float, n: float, level: float = 0.95) -> tuple[float, float]:
    """Wilson CI for proportion (reference only, ignores clustering)."""
    if n == 0:
        return (np.nan, np.nan)
    z = norm.ppf(0.5 + level / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


def cluster_bootstrap_rate_table(
    df: pd.DataFrame,
    group_col: str,
    n_boot: int = 1000,
    seed: int = 0,
    level: float = 0.95,
) -> pd.DataFrame:
    """Compute acceptance rates with sender-clustered bootstrap CIs."""
    d = df.dropna(subset=[group_col, "y_right", "user_key"]).copy()
    senders = d["user_key"].astype("category")
    s_codes = senders.cat.codes.to_numpy()
    n_s = len(senders.cat.categories)

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n_s, size=(n_boot, n_s))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2

    categories = sorted(d[group_col].unique(), key=lambda x: (str(type(x)), x))
    rows = []

    for cat in categories:
        m = (d[group_col] == cat).to_numpy()
        n_c = np.bincount(s_codes[m], minlength=n_s).astype(float)
        k_c = np.bincount(s_codes[m], weights=d["y_right"].to_numpy()[m], minlength=n_s)
        n_total = float(n_c.sum())
        k_total = float(k_c.sum())
        if n_total == 0:
            rows.append((cat, 0, 0, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        with np.errstate(invalid="ignore", divide="ignore"):
            boot = k_c[boot_idx].sum(axis=1) / n_c[boot_idx].sum(axis=1)
        ci_lo, ci_hi = np.nanquantile(boot, [lo_q, hi_q])
        w_lo, w_hi = wilson_interval(k_total, n_total, level)
        rows.append((cat, int(n_total), int(k_total), k_total / n_total, ci_lo, ci_hi, w_lo, w_hi))

    return pd.DataFrame(
        rows,
        columns=[
            "kategoria",
            "n_swipe",
            "n_prawych",
            "odsetek_prawych",
            "ci_low_boot",
            "ci_high_boot",
            "wilson_low",
            "wilson_high",
        ],
    )


def _cluster_groups(d: pd.DataFrame) -> np.ndarray:
    """Two-way cluster ids: sender and receiver."""
    return np.column_stack(
        [
            pd.factorize(d["user_key"])[0],
            pd.factorize(d["target_user_key"])[0],
        ]
    )


def fit_h1_logit_models(df: pd.DataFrame) -> dict[str, Any]:
    """Fit nested logit models and calculate incremental block contributions (D16)."""
    cols_needed = DEMOG_COLS + INTERESTS_COLS + LIFESTYLE_COLS + CONTROL_COLS + ["y_right"]
    d = df.dropna(subset=cols_needed).copy().reset_index(drop=True)
    groups = _cluster_groups(d)
    y = d["y_right"].to_numpy()

    blocks = {
        "null": [],
        "demog": DEMOG_COLS + CONTROL_COLS,
        "age_interests": DEMOG_COLS + INTERESTS_COLS + CONTROL_COLS,
        "lifestyle": LIFESTYLE_COLS + CONTROL_COLS,
        "full": list(dict.fromkeys(DEMOG_COLS + INTERESTS_COLS + LIFESTYLE_COLS + CONTROL_COLS)),
    }

    models = {}
    summaries = []

    for name, cols in blocks.items():
        if not cols:
            X = np.ones((len(d), 1))
            col_names = ["const"]
        else:
            X = sm.add_constant(d[cols])
            col_names = list(X.columns)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = sm.Logit(y, X)
            try:
                fit = m.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
            except Exception:
                fit = m.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups[:, 0]})

        models[name] = fit
        summaries.append(
            {
                "model": name,
                "n_vars": len(col_names) - 1,
                "llf": fit.llf,
                "aic": fit.aic,
                "bic": fit.bic,
            }
        )

    sum_df = pd.DataFrame(summaries)
    ll_null = models["null"].llf
    sum_df["pseudo_r2"] = 1 - sum_df["llf"] / ll_null

    # Both inclusion orders (D16)
    delta_lifestyle_over_interests = models["full"].llf - models["age_interests"].llf
    delta_interests_over_lifestyle = models["full"].llf - models["lifestyle"].llf

    r2_lifestyle_increment = (1 - models["full"].llf / ll_null) - (
        1 - models["age_interests"].llf / ll_null
    )
    r2_interests_increment = (1 - models["full"].llf / ll_null) - (
        1 - models["lifestyle"].llf / ll_null
    )

    full_fit = models["full"]
    or_df = pd.DataFrame(
        {
            "zmienna": full_fit.params.index,
            "coef": full_fit.params.values,
            "se": full_fit.bse.values,
            "or": np.exp(full_fit.params.values),
            "ci_low": np.exp(full_fit.params.values - 1.96 * full_fit.bse.values),
            "ci_high": np.exp(full_fit.params.values + 1.96 * full_fit.bse.values),
            "p_value": full_fit.pvalues.values,
        }
    )

    return {
        "models": models,
        "summary": sum_df,
        "odds_ratios": or_df,
        "delta_lifestyle_over_interests_ll": delta_lifestyle_over_interests,
        "delta_interests_over_lifestyle_ll": delta_interests_over_lifestyle,
        "r2_lifestyle_increment": r2_lifestyle_increment,
        "r2_interests_increment": r2_interests_increment,
        "data_len": len(d),
    }


def permutation_null_lifestyle(
    df: pd.DataFrame, n_perm: int = 1000, seed: int = 0
) -> tuple[float, np.ndarray, float]:
    """Test lifestyle increment against null baseline by shuffling receiver lifestyle traits."""
    cols_needed = DEMOG_COLS + INTERESTS_COLS + LIFESTYLE_COLS + CONTROL_COLS + ["y_right"]
    d = df.dropna(subset=cols_needed).copy().reset_index(drop=True)

    base_cols = DEMOG_COLS + INTERESTS_COLS + CONTROL_COLS
    X_base = sm.add_constant(d[base_cols]).to_numpy()
    y = d["y_right"].to_numpy()

    recv_codes, recv_keys = pd.factorize(d["target_user_key"])
    n_recv = len(recv_keys)
    rec_life = (
        d.groupby("target_user_key")[LIFESTYLE_COLS].mean().reindex(recv_keys).fillna(0).to_numpy()
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_base = sm.Logit(y, X_base).fit(disp=0)
        ll_base = m_base.llf

        life_mat = d[LIFESTYLE_COLS].to_numpy()
        m_full = sm.Logit(y, np.column_stack([X_base, life_mat])).fit(disp=0)
        observed_delta_ll = m_full.llf - ll_base

    rng = np.random.default_rng(seed)
    null_deltas = np.empty(n_perm)

    for i in range(n_perm):
        perm_idx = rng.permutation(n_recv)
        perm_life = rec_life[perm_idx][recv_codes]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m_perm = sm.Logit(y, np.column_stack([X_base, perm_life])).fit(disp=0)
            null_deltas[i] = m_perm.llf - ll_base

    p_val = float((np.sum(null_deltas >= observed_delta_ll) + 1) / (n_perm + 1))
    return float(observed_delta_ll), null_deltas, p_val


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(p)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _logloss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def grouped_cv_h1(df: pd.DataFrame, n_splits: int = 5, seed: int = 0) -> pd.DataFrame:
    """Out-of-sample 5-fold cross-validation grouped by sender to prevent leakage."""
    cols_needed = DEMOG_COLS + INTERESTS_COLS + LIFESTYLE_COLS + CONTROL_COLS + ["y_right"]
    d = df.dropna(subset=cols_needed).copy().reset_index(drop=True)

    rng = np.random.default_rng(seed)
    senders = d["user_key"].unique()
    fold_of = dict(zip(senders, rng.permutation(len(senders)) % n_splits, strict=True))
    folds = d["user_key"].map(fold_of).to_numpy()
    y = d["y_right"].to_numpy()

    blocks = {
        "null": np.ones((len(d), 1)),
        "lifestyle": sm.add_constant(d[LIFESTYLE_COLS + CONTROL_COLS]).to_numpy(),
        "age_interests": sm.add_constant(d[DEMOG_COLS + INTERESTS_COLS + CONTROL_COLS]).to_numpy(),
        "full": sm.add_constant(
            d[DEMOG_COLS + INTERESTS_COLS + LIFESTYLE_COLS + CONTROL_COLS]
        ).to_numpy(),
    }

    rows = []
    for k in range(n_splits):
        tr, te = (folds != k), (folds == k)
        for b_name, X_mat in blocks.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = sm.Logit(y[tr], X_mat[tr]).fit(disp=0, maxiter=100)
            p = m.predict(X_mat[te])
            rows.append(
                {"fold": k, "block": b_name, "logloss": _logloss(y[te], p), "auc": _auc(y[te], p)}
            )

    return pd.DataFrame(rows)


def sensitivity_analysis_h1(df: pd.DataFrame) -> pd.DataFrame:
    """Evaluate H1 block comparisons across robustness and sensitivity scenarios."""
    scenarios = {
        "main (as-of D7, brak Hyderabadu D10)": df,
        "tylko prior_version (D7)": df[df["source_flag_receiver"] == "prior_version"],
        "oba prior_version (D7)": df[df["both_prior_version"] == 1],
        "bez kont skrajnych (D6)": df[df["is_extreme_user"] == 0],
        "aktywni nadawcy >= 10 (D6)": df[df["is_low_activity"] == 0],
    }

    res_list = []
    for name, sub_df in scenarios.items():
        res = fit_h1_logit_models(sub_df)
        res_list.append(
            {
                "scenariusz": name,
                "n_swipe": res["data_len"],
                "delta_ll_lifestyle": res["delta_lifestyle_over_interests_ll"],
                "delta_r2_lifestyle": res["r2_lifestyle_increment"],
                "delta_ll_interests": res["delta_interests_over_lifestyle_ll"],
                "delta_r2_interests": res["r2_interests_increment"],
            }
        )
    return pd.DataFrame(res_list)
