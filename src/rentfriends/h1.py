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
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, rankdata
from sklearn.metrics import average_precision_score

from rentfriends.dataset_h1 import build_h1_dataset

# Style constants matching STYLEGUIDE.md
PURPLE = "#A247E3"
PURPLE_INK = "#8B34C4"
BLUE = "#234CE0"
GRAY = "#595959"
HAIR = "#D5D2CB"
CORAL = "#D9534F"

# Feature definitions for H1 blocks
DEMOG_COLS = ["same_band", "age_band_diff", "same_sex"]  # legacy demographic block
AGE_COLS = ["same_band", "age_band_diff_abs", "age_band_diff"]
INTERESTS_COLS = ["interests_jaccard", "interests_shared_n", "interests_count_diff_abs"]
LIFESTYLE_COLS = ["lifestyle_agree_ratio", "lifestyle_tag_conflict", "lifestyle_shared_tags_n"]
CONTROL_COLS = ["city_same", "city_diff"]
BLOCK_NAMES = ("age", "interests", "lifestyle")


@dataclass(frozen=True)
class H1Spec:
    """Model specification: which controls and which columns form each block.

    Controls are identical in every model (Z1); blocks are added on top of them.
    """

    name: str = "main"
    sex_control: str = "sex_pair"
    age_cols: tuple[str, ...] = tuple(AGE_COLS)
    age_sq: bool = False  # add |diff|^2 (card 3.2) as a sensitivity variant
    sender_band_fe: bool = False  # sender age-band dummies (reference 18-20)
    interest_cols: tuple[str, ...] = tuple(INTERESTS_COLS)
    lifestyle_cols: tuple[str, ...] = tuple(LIFESTYLE_COLS)
    city_control: bool = True


# Pre-audit design (anchor for reproducing the published numbers): same_sex sits inside the age
# block and the only controls are the city dummies.
LEGACY_SPEC = H1Spec(
    name="spec_old",
    sex_control="none",
    age_cols=("same_band", "age_band_diff", "same_sex"),
)
# Controls unified (Z1) but sex coded as same_sex instead of the ordered sex_pair.
SAME_SEX_SPEC = H1Spec(name="same_sex", sex_control="same_sex")


def _spec_block_cols(spec: H1Spec) -> dict[str, list[str]]:
    age = list(spec.age_cols) + (["age_band_diff_abs_sq"] if spec.age_sq else [])
    return {
        "age": age,
        "interests": list(spec.interest_cols),
        "lifestyle": list(spec.lifestyle_cols),
    }


def _spec_required_cols(spec: H1Spec) -> list[str]:
    cols: list[str] = ["y_right", "user_key", "target_user_key"]
    for block_cols in _spec_block_cols(spec).values():
        cols += block_cols
    if spec.sex_control != "none":
        cols.append(spec.sex_control)
    if spec.city_control:
        cols += CONTROL_COLS
    if spec.sender_band_fe:
        cols.append("age_band_sender")
    return list(dict.fromkeys(cols))


def prepare_h1_sample(df: pd.DataFrame, spec: H1Spec | None = None) -> pd.DataFrame:
    """Complete-case sample shared by every model of one specification."""
    spec = spec or H1Spec()
    if spec.age_sq and "age_band_diff_abs_sq" not in df.columns:
        df = df.assign(age_band_diff_abs_sq=df["age_band_diff_abs"] ** 2)
    return df.dropna(subset=_spec_required_cols(spec)).copy().reset_index(drop=True)


def control_frame(d: pd.DataFrame, spec: H1Spec) -> pd.DataFrame:
    """Control columns, identical for all models of a specification."""
    parts: list[pd.DataFrame] = []
    if spec.sex_control == "sex_pair":
        dummies = pd.get_dummies(d["sex_pair"], prefix="sex", dtype=float)
        dummies = dummies.drop(columns=["sex_F_F"], errors="ignore")
        parts.append(dummies)
    elif spec.sex_control != "none":
        parts.append(d[[spec.sex_control]].astype(float))
    if spec.city_control:
        parts.append(d[CONTROL_COLS].astype(float))
    if spec.sender_band_fe:
        sband = pd.get_dummies(d["age_band_sender"], prefix="sband", dtype=float)
        parts.append(sband.drop(columns=["sband_18-20"], errors="ignore"))
    if not parts:
        return pd.DataFrame(index=d.index)
    return pd.concat(parts, axis=1)


def block_frames(d: pd.DataFrame, spec: H1Spec) -> dict[str, pd.DataFrame]:
    """One frame of predictors per block (age, interests, lifestyle)."""
    return {k: d[cols].astype(float) for k, cols in _spec_block_cols(spec).items()}


def model_subsets() -> dict[str, tuple[str, ...]]:
    """All 8 block subsets; model names follow the block names joined by '_'."""
    subsets: dict[str, tuple[str, ...]] = {"controls": ()}
    for r in (1, 2, 3):
        for combo in combinations(BLOCK_NAMES, r):
            name = "full" if r == 3 else "_".join(combo)
            subsets[name] = combo
    return subsets


def design_matrix(
    d: pd.DataFrame,
    spec: H1Spec,
    blocks: tuple[str, ...],
    ctrl: pd.DataFrame | None = None,
    bf: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Constant + controls + selected blocks."""
    ctrl = control_frame(d, spec) if ctrl is None else ctrl
    bf = block_frames(d, spec) if bf is None else bf
    X = pd.concat([ctrl, *[bf[b] for b in blocks]], axis=1)
    return sm.add_constant(X, has_constant="add")


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


def fit_h1_logit_models(df: pd.DataFrame, spec: H1Spec | None = None) -> dict[str, Any]:
    """Fit nested logit models and calculate incremental block contributions (D16).

    All models share the same controls and the same complete-case sample (Z1). The `full`
    model carries two-way (sender, receiver) clustered standard errors (D18); log-likelihoods
    do not depend on the covariance estimator.
    """
    spec = spec or H1Spec()
    d = prepare_h1_sample(df, spec)
    groups = _cluster_groups(d)
    y = d["y_right"].to_numpy()
    ctrl = control_frame(d, spec)
    bf = block_frames(d, spec)

    models: dict[str, Any] = {}
    summaries = []

    null_fit = sm.Logit(y, np.ones((len(d), 1))).fit(disp=0)
    models["null"] = null_fit
    summaries.append(_summary_row("null", 0, null_fit))

    for name, combo in model_subsets().items():
        X = design_matrix(d, spec, combo, ctrl, bf)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = sm.Logit(y, X)
            if name == "full":
                try:
                    fit = m.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
                except Exception:
                    fit = m.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups[:, 0]})
            else:
                fit = m.fit(disp=0)
        models[name] = fit
        summaries.append(_summary_row(name, X.shape[1] - 1, fit))

    sum_df = pd.DataFrame(summaries)
    ll_null = models["null"].llf
    sum_df["pseudo_r2"] = 1 - sum_df["llf"] / ll_null

    # Both inclusion orders (D16): lifestyle over age+interests and the reverse
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
        "control_names": list(ctrl.columns),
        "spec": spec,
        "data_len": len(d),
    }


def _summary_row(name: str, n_vars: int, fit: Any) -> dict[str, Any]:
    return {
        "model": name,
        "n_vars": n_vars,
        "llf": fit.llf,
        "aic": fit.aic,
        "bic": fit.bic,
    }


def permutation_null_lifestyle(
    df: pd.DataFrame, n_perm: int = 1000, seed: int = 0, spec: H1Spec | None = None
) -> tuple[float, np.ndarray, float]:
    """Test lifestyle increment against null baseline by shuffling receiver lifestyle traits."""
    spec = spec or H1Spec()
    d = prepare_h1_sample(df, spec)
    lifestyle_cols = list(spec.lifestyle_cols)

    X_base = design_matrix(d, spec, ("age", "interests")).to_numpy()
    y = d["y_right"].to_numpy()

    recv_codes, recv_keys = pd.factorize(d["target_user_key"])
    n_recv = len(recv_keys)
    rec_life = (
        d.groupby("target_user_key")[lifestyle_cols].mean().reindex(recv_keys).fillna(0).to_numpy()
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_base = sm.Logit(y, X_base).fit(disp=0)
        ll_base = m_base.llf

        life_mat = d[lifestyle_cols].to_numpy()
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


def grouped_cv_h1(
    df: pd.DataFrame, n_splits: int = 5, seed: int = 0, spec: H1Spec | None = None
) -> pd.DataFrame:
    """Out-of-sample 5-fold cross-validation grouped by sender to prevent leakage."""
    spec = spec or H1Spec()
    d = prepare_h1_sample(df, spec)
    folds = sender_folds(d, n_splits, seed)
    y = d["y_right"].to_numpy()

    blocks = {"null": np.ones((len(d), 1))}
    for name, combo in model_subsets().items():
        blocks[name] = design_matrix(d, spec, combo).to_numpy()

    rows = []
    for k in range(n_splits):
        tr, te = (folds != k), (folds == k)
        for b_name, X_mat in blocks.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = sm.Logit(y[tr], X_mat[tr]).fit(disp=0, maxiter=100)
            p = m.predict(X_mat[te])
            rows.append(
                {
                    "fold": k,
                    "block": b_name,
                    "logloss": _logloss(y[te], p),
                    "auc": _auc(y[te], p),
                    "auc_pr": float(average_precision_score(y[te], p)),
                }
            )

    return pd.DataFrame(rows)


def sender_folds(d: pd.DataFrame, n_splits: int, seed: int) -> np.ndarray:
    """Assign each sender (all of their swipes) to one of `n_splits` folds."""
    rng = np.random.default_rng(seed)
    senders = d["user_key"].unique()
    fold_of = dict(zip(senders, rng.permutation(len(senders)) % n_splits, strict=True))
    return d["user_key"].map(fold_of).to_numpy()


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
