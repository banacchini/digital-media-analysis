"""Unified signal-block comparison for the thesis.

One sample, one estimator, one metric for all signal blocks (demography, interests, lifestyle,
bio). The question is how much each block adds to the out-of-sample prediction of a right swipe,
not whether a single coefficient is significant.

Design (all choices are documented in `docs/notes/unified-analysis.md`):

- Table: H1 dataset (demography, interests, lifestyle, as-of D7, Hyderabad dropped D10) joined
  row by row with the H3a receiver bio features. The join is checked, not assumed.
- Model: plain logit per block set (own Newton solver, standardised columns, tiny ridge).
  Predictions are out-of-fold, folds are grouped by sender.
- Metric: AUC *computed inside each fold and averaged* (pooled AUC is biased down by different
  fold intercepts; controls give 0.47). Repeated for several fold seeds and averaged.
- Uncertainty: cluster bootstrap over senders (multinomial sender weights, exact weighted AUC),
  so a *difference* between two blocks gets an interval.
- Null: the block's columns are permuted jointly across rows, the whole CV is repeated.

Receiver variant (`variant="pair+receiver"`): interests and lifestyle are pair-similarity blocks
while bio is a receiver block, so the blocks are not symmetric. The variant adds receiver
features to interests (number of receiver interest tags) and lifestyle (number of known
lifestyle fields and number of lifestyle tags of the receiver). These are plain counts of the
as-of profile and do not use the outcome, so there is no leakage across folds. Tag popularity
(share of right swipes per tag) is deliberately NOT used: it is a target encoding and would have
to be fitted inside each training fold, and for receivers it collapses into the receiver's
identity (popularity), which is not an "interest" signal.

Row-level data never leaves memory. Functions that print or return aggregates only.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import time
import warnings
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from threadpoolctl import threadpool_limits

from rentfriends import dataset_h1 as h1mod
from rentfriends.dataset_h1 import build_h1_dataset
from rentfriends.h2 import or_by_sender_sex, wilson_interval
from rentfriends.h3a import data as h3a_data

SEX_PAIR_DUMMIES = ["M_F", "F_M", "M_M", "F_O", "M_O", "O_F", "O_M"]
SEXES = ["F", "M", "O"]
MIN_CELL = 5  # cells with fewer rows are suppressed in every returned table
MIN_SENDERS_REPORT = 50  # sender groups smaller than this get no conclusion

BLOCKS: dict[str, list[str]] = {
    # Sex enters as the sender x receiver cell, because the same-sex effect has opposite signs
    # for female and male senders (H2). F_F is the reference; O_O (n = 20) is left in it.
    "demography": [f"sp_{c}" for c in SEX_PAIR_DUMMIES] + ["same_band", "age_band_diff"],
    "interests": ["interests_jaccard", "interests_shared_n", "interests_count_diff_abs"],
    "lifestyle": [
        "lifestyle_agree_ratio",
        "lifestyle_tag_conflict",
        "lifestyle_shared_tags_n",
        "lifestyle_known_any",
    ],
    "bio": ["has_bio", "bio_len_log"],
}
# Extra receiver-side columns of the "pair+receiver" variant (see module docstring).
RECEIVER_EXTRA: dict[str, list[str]] = {
    "interests": ["interests_count_receiver"],
    "lifestyle": ["rcv_lifestyle_known_n", "rcv_lifestyle_tags_n"],
}
VARIANTS = ("pair", "pair+receiver")
CONTROLS = ["city_same", "city_diff"]
ALL_BLOCKS = list(BLOCKS)


def block_columns(block: str, variant: str = "pair") -> list[str]:
    """Columns of a block under the given variant."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}")
    cols = list(BLOCKS[block])
    if variant == "pair+receiver":
        cols += RECEIVER_EXTRA.get(block, [])
    return cols


# ------------------------------------------------------------------------------ data


def _raw_from_dir(data_dir: Path, mapping_csv: Path) -> h3a_data.RawData:
    return h3a_data.RawData(
        users=pd.read_parquet(data_dir / "users.parquet"),
        history=pd.read_parquet(data_dir / "profile_history.parquet"),
        swipes=pd.read_parquet(data_dir / "swipes.parquet"),
        mapping=pd.read_csv(mapping_csv),
    )


def _receiver_extras(data_dir: Path, docs_dir: Path) -> pd.DataFrame:
    """Receiver-side as-of lifestyle information, aligned with the H1 swipe rows.

    Repeats the H1 steps (tag split, D13 imputation, D7 as-of resolve) for the receiver only.
    Returns per swipe: number of lifestyle tags, and for every structured lifestyle field a 0/1
    "known" flag before and after the D13 imputation of tags into empty fields.
    """
    swipes = pd.read_parquet(data_dir / "swipes.parquet")
    history = pd.read_parquet(data_dir / "profile_history.parquet")
    users = pd.read_parquet(data_dir / "users.parquet")
    mapping, category, _ = h1mod.load_tag_mappings(
        docs_dir / "interests_mapping.csv", docs_dir / "tag_category_proposal.csv"
    )
    hyd = set(users.loc[users["city"] == "Hyderabad", "user_key"])
    prof = swipes[swipes["target_type"] == "profile"]
    keep = ~(prof["user_key"].isin(hyd) | prof["target_user_key"].isin(hyd))
    sw = prof[keep].reset_index(drop=True)

    fields = h1mod.LIFESTYLE_STRUCTURED_FIELDS
    infrequent = h1mod.get_infrequent_canonical_tags(users["interests"], mapping, min_samples=50)
    for df in (history, users):
        split = df["interests"].apply(
            lambda raw: h1mod.transform_and_disentangle_tags(raw, mapping, category, infrequent)
        )
        df["pure_interests"] = [s[0] for s in split]
        df["lifestyle_tags"] = [s[1] for s in split]
        for f in fields:
            df[f"raw_{f}"] = df[f]
        imputed = h1mod.apply_d13_tag_imputation(df, lifestyle_tags_col="lifestyle_tags")
        for f in fields:
            df[f] = imputed[f]
    cols = [*fields, *[f"raw_{f}" for f in fields], "lifestyle_tags"]
    rec = h1mod.resolve_as_of_profiles(
        sw, history, users, user_col="target_user_key", prefix="receiver_", profile_cols=cols
    )
    out = pd.DataFrame(index=rec.index)
    out["_target"] = sw["target_user_key"].astype(str).to_numpy()
    out["_day"] = sw["day"].astype(int).to_numpy()
    out["rcv_lifestyle_tags_n"] = rec["receiver_lifestyle_tags"].map(len).astype(float)
    for f in fields:
        out[f"rcv_known_after_{f}"] = rec[f"receiver_{f}"].notna().astype(int)
        out[f"rcv_known_raw_{f}"] = rec[f"receiver_raw_{f}"].notna().astype(int)
    out["rcv_lifestyle_known_n"] = out[[f"rcv_known_after_{f}" for f in fields]].sum(axis=1)
    out["_n_profile_swipes"] = int(len(prof))
    return out


def build_unified_table(
    data_dir: str | Path = "data/interim/unified",
    docs_dir: str | Path = "docs",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Swipe-level table with all four blocks. Returns the table and a sample-flow dict."""
    data_dir, docs_dir = Path(data_dir), Path(docs_dir)
    h1 = build_h1_dataset(data_dir=data_dir, docs_dir=docs_dir)

    raw = _raw_from_dir(data_dir, docs_dir / "interests_mapping.csv")
    h3 = h3a_data.build_analysis_table(raw).table
    h3 = h3[h3["hyderabad"] == 0].reset_index(drop=True)

    # The join is positional, so verify that both tables describe the same swipes.
    if len(h1) != len(h3):
        raise ValueError(f"row count differs: H1 {len(h1)} vs H3a {len(h3)}")
    same_rows = (
        (h1["y_right"].to_numpy() == h3["y_right"].to_numpy()).all()
        and (h1["day"].to_numpy() == h3["day"].to_numpy()).all()
        and (h1["user_key"].to_numpy() == h3["s_key"].to_numpy()).all()
        and (h1["target_user_key"].to_numpy() == h3["r_key"].to_numpy()).all()
    )
    if not same_rows:
        raise ValueError("H1 and H3a tables are not row-aligned")

    extras = _receiver_extras(data_dir, docs_dir)
    if len(extras) != len(h1) or not (
        (extras["_target"].to_numpy() == h1["target_user_key"].to_numpy()).all()
        and (extras["_day"].to_numpy() == h1["day"].to_numpy()).all()
    ):
        raise ValueError("receiver extras are not row-aligned with the H1 table")
    n_profile = int(extras["_n_profile_swipes"].iloc[0])

    t = h1.copy()
    for c in extras.columns:
        if not c.startswith("_"):
            t[c] = extras[c].to_numpy()
    t["has_bio"] = h3["has_bio"].to_numpy()
    t["bio_len_log"] = np.log1p(h3["bio_len"].to_numpy().astype(float))
    for c in SEX_PAIR_DUMMIES:
        t[f"sp_{c}"] = (t["sex_pair"] == c).astype(float)
    t["city_same"] = (t["same_city"] == "same").astype(float)
    t["city_diff"] = (t["same_city"] == "different").astype(float)
    # Lifestyle fields are missing for most users. Keep the swipe and flag the missingness
    # instead of dropping 3/4 of the sample.
    t["lifestyle_known_any"] = (t["lifestyle_known_count"] > 0).astype(float)
    t["lifestyle_agree_ratio"] = t["lifestyle_agree_ratio"].fillna(0.0)

    flow = {"swipes_profile_total": n_profile, "swipes_after_hyderabad": len(t)}
    needed = (
        [c for cols in BLOCKS.values() for c in cols]
        + [c for cols in RECEIVER_EXTRA.values() for c in cols]
        + CONTROLS
        + ["y_right"]
    )
    t = t.dropna(subset=needed).reset_index(drop=True)
    flow["swipes_complete_case"] = len(t)
    flow["senders"] = int(t["user_key"].nunique())
    flow["receivers"] = int(t["target_user_key"].nunique())
    return t, flow


# --------------------------------------------------------------------------- metrics


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(p)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _logloss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _fold_auc(y: np.ndarray, p: np.ndarray, folds: np.ndarray) -> np.ndarray:
    """AUC inside every fold (NaN for a fold with a single class)."""
    return np.array([_auc(y[folds == k], p[folds == k]) for k in np.unique(folds)])


# ----------------------------------------------------------------------------- model


def design(d: pd.DataFrame, blocks: list[str], variant: str = "pair") -> np.ndarray:
    cols = [c for b in blocks for c in block_columns(b, variant)] + CONTROLS
    x = d[cols].astype(float).to_numpy()
    return np.column_stack([np.ones(len(x)), x])


def _fit_predict(
    xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray, l2: float = 1e-6, max_iter: int = 50
) -> np.ndarray:
    """Logit by Newton steps on standardised columns (column 0 is the constant)."""
    mu = xtr[:, 1:].mean(axis=0)
    sd = xtr[:, 1:].std(axis=0)
    sd[sd < 1e-12] = 1.0  # constant column (e.g. sender-sex cells in a one-sex subset): stays 0

    def scale(x: np.ndarray) -> np.ndarray:
        return np.column_stack([np.ones(len(x)), (x[:, 1:] - mu) / sd])

    a, b = scale(xtr), scale(xte)
    k = a.shape[1]
    ridge = np.eye(k) * l2
    ridge[0, 0] = 0.0
    m = float(np.clip(ytr.mean(), 1e-6, 1 - 1e-6))
    beta = np.zeros(k)
    beta[0] = np.log(m / (1 - m))
    for _ in range(max_iter):
        eta = np.clip(a @ beta, -30, 30)
        p = 1.0 / (1.0 + np.exp(-eta))
        grad = a.T @ (ytr - p) - ridge @ beta
        hess = (a * (p * (1 - p))[:, None]).T @ a + ridge
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return 1.0 / (1.0 + np.exp(-np.clip(b @ beta, -30, 30)))


def sender_folds(d: pd.DataFrame, n_splits: int, seed: int) -> np.ndarray:
    """Fold index per row; all swipes of a sender share a fold."""
    senders = d["user_key"].unique()
    rng = np.random.default_rng(seed)
    fold_of = dict(zip(senders, rng.permutation(len(senders)) % n_splits, strict=True))
    return d["user_key"].map(fold_of).to_numpy()


def _oof_from_matrix(x: np.ndarray, y: np.ndarray, folds: np.ndarray) -> np.ndarray:
    pred = np.empty(len(y))
    for k in np.unique(folds):
        tr, te = folds != k, folds == k
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pred[te] = _fit_predict(x[tr], y[tr], x[te])
    return pred


def oof_predictions(
    d: pd.DataFrame,
    blocks: list[str],
    n_splits: int = 5,
    seed: int = 0,
    variant: str = "pair",
) -> np.ndarray:
    """Out-of-fold predicted probabilities for the logit with the given blocks."""
    x = design(d, blocks, variant)
    return _oof_from_matrix(x, d["y_right"].to_numpy(), sender_folds(d, n_splits, seed))


def _n_workers() -> int:
    return max(1, min(12, os.cpu_count() or 1))


def _pmap(fn, items: Iterable, workers: int | None = None) -> list:
    """Thread map with BLAS limited to one thread per worker (avoids oversubscription)."""
    items = list(items)
    w = workers or _n_workers()
    with threadpool_limits(limits=1), ThreadPoolExecutor(max_workers=w) as ex:
        return list(ex.map(fn, items))


# --------------------------------------------------------------------------- bootstrap


@dataclass
class Boot:
    """Cluster-bootstrap draws of AUC for several named prediction vectors."""

    names: list[str]
    point: dict[str, float]
    draws: dict[str, np.ndarray]

    def diff(self, a: str, b: str) -> tuple[float, float, float]:
        """Point estimate and 95% interval of AUC(a) - AUC(b)."""
        d = self.draws[a] - self.draws[b]
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        return self.point[a] - self.point[b], float(lo), float(hi)


def _prep_auc_groups(y: np.ndarray, pred: np.ndarray, folds: np.ndarray) -> list[tuple]:
    """Per fold: row index, tie-group code, number of groups, y. Lets weighted AUC skip sorting."""
    out = []
    for k in np.unique(folds):
        idx = np.flatnonzero(folds == k)
        _, g = np.unique(pred[idx], return_inverse=True)
        out.append((idx, g, int(g.max()) + 1, y[idx].astype(float)))
    return out


def _weighted_auc(groups: list[tuple], w: np.ndarray) -> float:
    """Mean over folds of the AUC with row weights `w` (ties count one half)."""
    vals = []
    for idx, g, ng, yk in groups:
        wk = w[idx]
        wp = np.bincount(g, weights=wk * yk, minlength=ng)
        wn = np.bincount(g, weights=wk * (1 - yk), minlength=ng)
        sp, sn = wp.sum(), wn.sum()
        if sp <= 0 or sn <= 0:
            vals.append(np.nan)
            continue
        below = np.cumsum(wn) - wn
        vals.append(float((wp * (below + 0.5 * wn)).sum() / (sp * sn)))
    return float(np.nanmean(vals)) if not np.all(np.isnan(vals)) else float("nan")


def cluster_bootstrap_auc(
    y: np.ndarray,
    preds: dict[str, np.ndarray],
    clusters: np.ndarray,
    n_boot: int = 500,
    seed: int = 1,
    folds: np.ndarray | dict[str, list[tuple[np.ndarray, np.ndarray]]] | None = None,
) -> Boot:
    """Resample senders with replacement and recompute AUC of every prediction vector.

    `folds=None`: pooled AUC of each vector. `folds=<fold index array>`: AUC inside each fold,
    averaged. `folds=<dict name -> [(pred, folds), ...]>` (one pair per CV seed; `preds` is then
    ignored): average over CV seeds and folds. The same sender weights are used for every model,
    so differences have properly paired draws.
    """
    codes, uniq = pd.factorize(clusters)
    n_s = len(uniq)
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(n_s, np.full(n_s, 1.0 / n_s), size=n_boot)  # n_boot x n_s

    if isinstance(folds, dict):
        spec = {k: [_prep_auc_groups(y, p, f) for p, f in v] for k, v in folds.items()}
    else:
        f = np.zeros(len(y), dtype=int) if folds is None else np.asarray(folds)
        spec = {k: [_prep_auc_groups(y, p, f)] for k, p in preds.items()}

    ones = np.ones(len(y))

    def run(name: str) -> tuple[float, np.ndarray]:
        sets = spec[name]
        point = float(np.mean([_weighted_auc(g, ones) for g in sets]))
        dr = np.empty(n_boot)
        for b in range(n_boot):
            w = counts[b][codes].astype(float)
            dr[b] = np.mean([_weighted_auc(g, w) for g in sets])
        return point, dr

    names = list(spec)
    res = _pmap(run, names)
    return Boot(
        names,
        {n: r[0] for n, r in zip(names, res, strict=True)},
        {n: r[1] for n, r in zip(names, res, strict=True)},
    )


# ---------------------------------------------------------------------------- null


def permuted_null(
    d: pd.DataFrame,
    block: str,
    base_blocks: list[str],
    n_perm: int = 20,
    seed: int = 7,
    variant: str = "pair",
) -> np.ndarray:
    """In-fold AUC gain of `block` over `base_blocks` when its columns are shuffled jointly.

    Folds are fixed (CV seed 0), only the block rows are permuted. Runs in threads.
    """
    y = d["y_right"].to_numpy()
    folds = sender_folds(d, 5, 0)
    base_auc = float(
        np.nanmean(_fold_auc(y, oof_predictions(d, base_blocks, variant=variant), folds))
    )
    x_full = design(d, [*base_blocks, block], variant)
    n_ctrl = len(CONTROLS)
    n_blk = len(block_columns(block, variant))
    # block columns sit right before the controls
    sl = slice(x_full.shape[1] - n_ctrl - n_blk, x_full.shape[1] - n_ctrl)
    rng = np.random.default_rng(seed)
    perms = [rng.permutation(len(d)) for _ in range(n_perm)]

    def one(perm: np.ndarray) -> float:
        xp = x_full.copy()
        xp[:, sl] = x_full[perm][:, sl]
        pred = _oof_from_matrix(xp, y, folds)
        return float(np.nanmean(_fold_auc(y, pred, folds))) - base_auc

    return np.array(_pmap(one, perms))


# ------------------------------------------------------------------------ comparison


def receiver_folds(d: pd.DataFrame, n_splits: int, seed: int) -> np.ndarray:
    """Fold index per row; all swipes *received by* one profile share a fold."""
    receivers = d["target_user_key"].unique()
    rng = np.random.default_rng(seed)
    fold_of = dict(zip(receivers, rng.permutation(len(receivers)) % n_splits, strict=True))
    return d["target_user_key"].map(fold_of).to_numpy()


def cv_auc_columns(
    d: pd.DataFrame,
    columns: list[str],
    group: str = "sender",
    seeds: Iterable[int] = (0, 1, 2),
    n_splits: int = 5,
) -> np.ndarray:
    """Mean in-fold AUC of a logit on arbitrary `columns` (plus the city controls), per CV seed.

    `group` is "sender" (as everywhere else) or "receiver" (folds grouped by the receiving profile,
    a check for leakage through popular receivers). Same estimator as `oof_predictions`.
    """
    if group not in ("sender", "receiver"):
        raise ValueError(f"unknown group {group!r}")
    x = np.column_stack([np.ones(len(d)), d[[*columns, *CONTROLS]].astype(float).to_numpy()])
    y = d["y_right"].to_numpy()
    make = sender_folds if group == "sender" else receiver_folds
    out = []
    for s in seeds:
        folds = make(d, n_splits, s)
        out.append(float(np.nanmean(_fold_auc(y, _oof_from_matrix(x, y, folds), folds))))
    return np.array(out)


def demography_decomposition(d: pd.DataFrame, seeds: Iterable[int] = (0, 1, 2)) -> pd.DataFrame:
    """AUC over the controls of parts of the demography block (mean over CV seeds).

    Rows: age, sender sex, receiver sex, sender + receiver sex (main effects only), sex-pair cells
    (main effects + interaction), sex + age, full demography. The interaction (true sex
    *agreement*) is the cells minus the main effects. Columns: part, auc, gain_over_controls.
    """
    seeds = list(seeds)
    t = d.copy()
    snd, rcv = t["sex_pair"].str[0], t["sex_pair"].str[-1]
    for who, ser in (("snd", snd), ("rcv", rcv)):
        for k in ("M", "O"):
            t[f"{who}_{k}"] = (ser == k).astype(float)
    age = ["same_band", "age_band_diff"]
    cells = BLOCKS["demography"][: len(SEX_PAIR_DUMMIES)]
    parts = {
        "kontrole (miasto)": [],
        "wiek": age,
        "płeć nadawcy": ["snd_M", "snd_O"],
        "płeć odbiorcy": ["rcv_M", "rcv_O"],
        "płeć nadawcy + odbiorcy (efekty główne)": ["snd_M", "snd_O", "rcv_M", "rcv_O"],
        "komórki płci pary (efekty główne + interakcja)": cells,
        "płeć (komórki) + wiek = demografia": cells + age,
    }
    base = float(cv_auc_columns(t, [], seeds=seeds).mean())
    rows = []
    for name, cols in parts.items():
        auc = float(cv_auc_columns(t, cols, seeds=seeds).mean())
        rows.append({"part": name, "auc": auc, "gain_over_controls": auc - base})
    return pd.DataFrame(rows)


def _model_sets() -> dict[str, list[str]]:
    sets: dict[str, list[str]] = {"controls": []}
    for b in ALL_BLOCKS:
        sets[f"only:{b}"] = [b]
        sets[f"full-{b}"] = [x for x in ALL_BLOCKS if x != b]
    sets["full"] = ALL_BLOCKS
    for b in ("interests", "lifestyle", "bio"):
        sets[f"dem+{b}"] = ["demography", b]
    return sets


def _oof_many(
    d: pd.DataFrame, sets: dict[str, list[str]], variant: str, cv_seeds: list[int]
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """Out-of-fold predictions for every model set and CV seed (computed in threads)."""
    y = d["y_right"].to_numpy()
    folds = {s: sender_folds(d, 5, s) for s in cv_seeds}
    mats = {name: design(d, bl, variant) for name, bl in sets.items()}
    tasks = [(name, s) for name in sets for s in cv_seeds]

    def one(task: tuple[str, int]) -> np.ndarray:
        name, s = task
        return _oof_from_matrix(mats[name], y, folds[s])

    preds = _pmap(one, tasks)
    out: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {n: [] for n in sets}
    for (name, s), p in zip(tasks, preds, strict=True):
        out[name].append((p, folds[s]))
    return out


def compare_blocks(
    d: pd.DataFrame,
    n_boot: int = 500,
    n_perm: int = 20,
    seed: int = 0,
    n_cv_seeds: int = 3,
    variant: str = "pair",
) -> dict[str, pd.DataFrame]:
    """The full comparison: alone, unique, over demography and difference, with intervals.

    AUC is computed inside each sender-grouped fold and averaged; the whole CV is repeated for
    `n_cv_seeds` fold seeds (seed, seed + 1, ...) and averaged. `variant` is "pair" or
    "pair+receiver" (see module docstring).

    Returns a dict of DataFrames:
    - `levels`: model, auc_fold_mean, auc_fold_sd (sd of the fold AUCs), auc_pooled (biased down,
      reported for reference), logloss, n_params;
    - `contrasts`: contrast, block, kind, d_auc, ci_lo, ci_hi with kind in {alone, unique,
      over_demography, difference}; intervals are sender-cluster bootstrap percentiles;
    - `null`: block, base, null_mean, null_p95, observed_gain, p_perm,
      p_perm = (1 + #{null >= observed}) / (1 + n_perm).
    """
    y = d["y_right"].to_numpy()
    clusters = d["user_key"].to_numpy()
    cv_seeds = [seed + i for i in range(n_cv_seeds)]
    sets = _model_sets()
    preds = _oof_many(d, sets, variant, cv_seeds)
    boot = cluster_bootstrap_auc(y, {}, clusters, n_boot=n_boot, seed=seed + 1, folds=preds)

    rows = []
    for name, lst in preds.items():
        fa = np.array([_fold_auc(y, p, f) for p, f in lst])  # seeds x folds
        rows.append(
            {
                "model": name,
                "auc_fold_mean": float(np.nanmean(fa)),
                "auc_fold_sd": float(np.nanmean(np.nanstd(fa, axis=1, ddof=1))),
                "auc_pooled": float(np.mean([_auc(y, p) for p, _ in lst])),
                "logloss": float(np.mean([_logloss(y, p) for p, _ in lst])),
                "n_params": design(d.head(5), sets[name], variant).shape[1],
            }
        )
    levels = pd.DataFrame(rows)

    crow = []

    def add(label: str, block: str, kind: str, a: str, b: str) -> None:
        est, lo, hi = boot.diff(a, b)
        crow.append(
            {
                "contrast": label,
                "block": block,
                "kind": kind,
                "d_auc": est,
                "ci_lo": lo,
                "ci_hi": hi,
            }
        )

    for b in ALL_BLOCKS:
        add(f"{b}: alone vs controls", b, "alone", f"only:{b}", "controls")
    for b in ALL_BLOCKS:
        add(f"{b}: unique (full - full without it)", b, "unique", "full", f"full-{b}")
    for b in ("interests", "lifestyle", "bio"):
        add(f"{b} over demography", b, "over_demography", f"dem+{b}", "only:demography")
    for b in ("lifestyle", "bio"):
        du = (boot.draws["full"] - boot.draws[f"full-{b}"]) - (
            boot.draws["full"] - boot.draws["full-interests"]
        )
        est = (boot.point["full"] - boot.point[f"full-{b}"]) - (
            boot.point["full"] - boot.point["full-interests"]
        )
        lo, hi = np.nanpercentile(du, [2.5, 97.5])
        crow.append(
            {
                "contrast": f"unique {b} - unique interests",
                "block": f"{b}-interests",
                "kind": "difference",
                "d_auc": est,
                "ci_lo": float(lo),
                "ci_hi": float(hi),
            }
        )
    contrasts = pd.DataFrame(crow)

    nrow = []
    for b in ("interests", "lifestyle", "bio"):
        gains = permuted_null(d, b, ["demography"], n_perm=n_perm, seed=seed + 7, variant=variant)
        # observed gain on the same (CV seed 0) folds as the null
        p0 = {n: lst[0] for n, lst in preds.items()}
        f0 = p0["controls"][1]
        obs = float(
            np.nanmean(_fold_auc(y, p0[f"dem+{b}"][0], f0))
            - np.nanmean(_fold_auc(y, p0["only:demography"][0], f0))
        )
        nrow.append(
            {
                "block": b,
                "base": "demography",
                "null_mean": float(gains.mean()),
                "null_p95": float(np.percentile(gains, 95)),
                "observed_gain": obs,
                "p_perm": float((1 + np.sum(gains >= obs)) / (1 + n_perm)),
            }
        )
    return {"levels": levels, "contrasts": contrasts, "null": pd.DataFrame(nrow)}


# -------------------------------------------------------------------------- sensitivity

SCENARIOS: dict[str, str | None] = {
    "main": None,
    "no extreme accounts": "is_extreme_user == 0",
    "active senders": "is_low_activity == 0",
    "both prior_version": "both_prior_version == 1",
    "female senders only": "sex_sender == 'F'",
    "male senders only": "sex_sender == 'M'",
}


def own_gains(
    d: pd.DataFrame, n_boot: int = 300, seed: int = 0, n_cv_seeds: int = 1, variant: str = "pair"
) -> pd.DataFrame:
    """Own (unique) AUC gain of each block: full model minus full model without the block."""
    sets = {"full": ALL_BLOCKS} | {
        f"full-{b}": [x for x in ALL_BLOCKS if x != b] for b in ALL_BLOCKS
    }
    preds = _oof_many(d, sets, variant, [seed + i for i in range(n_cv_seeds)])
    boot = cluster_bootstrap_auc(
        d["y_right"].to_numpy(),
        {},
        d["user_key"].to_numpy(),
        n_boot=n_boot,
        seed=seed + 1,
        folds=preds,
    )
    rows = []
    for b in ALL_BLOCKS:
        est, lo, hi = boot.diff("full", f"full-{b}")
        rows.append({"block": b, "d_auc": est, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows)


def sensitivity(
    d: pd.DataFrame, n_boot: int = 300, seed: int = 0, variant: str = "pair"
) -> pd.DataFrame:
    """Own gain of each block in six scenarios (see `SCENARIOS`).

    Columns: scenario, n_swipes, block, d_auc, ci_lo, ci_hi. In the one-sex scenarios the sender
    sex cells of the demography block are constant, so demography reduces to receiver sex, age
    band and age difference. A scenario with fewer than `MIN_SENDERS_REPORT` senders is skipped.
    """
    out = []
    for name, query in SCENARIOS.items():
        sub = d if query is None else d.query(query)
        if sub["user_key"].nunique() < MIN_SENDERS_REPORT:
            continue
        g = own_gains(sub.reset_index(drop=True), n_boot=n_boot, seed=seed, variant=variant)
        g.insert(0, "n_swipes", len(sub))
        g.insert(0, "scenario", name)
        out.append(g)
    cols = ["scenario", "n_swipes", "block", "d_auc", "ci_lo", "ci_hi"]
    return pd.concat(out, ignore_index=True)[cols] if out else pd.DataFrame(columns=cols)


# --------------------------------------------------------------------------- sex summary


def sex_summary(d: pd.DataFrame, n_boot: int = 1000, seed: int = 0) -> dict[str, pd.DataFrame]:
    """P(right) per sender-sex x receiver-sex cell and the same-sex odds ratio per sender sex.

    - `matrix`: sender_sex, receiver_sex, n, rate, ci_lo, ci_hi (bootstrap over senders),
      wilson_lo, wilson_hi (ignores clustering, narrower). Cells with n < 5 are suppressed
      (all numbers NaN).
    - `odds`: sender_sex, or_raw, lo_raw, hi_raw, or_adj, lo_adj, hi_adj, plus n_senders and
      `reportable` (False when the sender sex has fewer than 50 senders: no conclusion).
      Logic of `h2.or_by_sender_sex` (same sex vs different sex, per sender sex, SEs clustered on
      sender and receiver); `_adj` adds age band, age-band difference and same-city controls.
    """
    y = d["y_right"].to_numpy().astype(float)
    codes, uniq = pd.factorize(d["user_key"])
    n_s = len(uniq)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_s, size=(n_boot, n_s))
    rows = []
    for a in SEXES:
        for b in SEXES:
            m = ((d["sex_sender"] == a) & (d["sex_receiver"] == b)).to_numpy()
            n_c = np.bincount(codes[m], minlength=n_s).astype(float)
            k_c = np.bincount(codes[m], weights=y[m], minlength=n_s)
            n, k = n_c.sum(), k_c.sum()
            if n < MIN_CELL:
                rows.append((a, b, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
                continue
            with np.errstate(invalid="ignore", divide="ignore"):
                boot = k_c[idx].sum(1) / n_c[idx].sum(1)
            lo, hi = np.nanquantile(boot, [0.025, 0.975])
            wl, wh = wilson_interval(k, n)
            rows.append((a, b, int(n), k / n, lo, hi, wl, wh))
    matrix = pd.DataFrame(
        rows,
        columns=[
            "sender_sex",
            "receiver_sex",
            "n",
            "rate",
            "ci_lo",
            "ci_hi",
            "wilson_lo",
            "wilson_hi",
        ],
    )

    h2d = pd.DataFrame(
        {
            "sender": d["user_key"].to_numpy(),
            "receiver": d["target_user_key"].to_numpy(),
            "sender_sex": d["sex_sender"].to_numpy(),
            "receiver_sex": d["sex_receiver"].to_numpy(),
            "same_sex": d["same_sex"].to_numpy().astype(float),
            "y_right": d["y_right"].to_numpy(),
            "age_band_diff": d["age_band_diff"].to_numpy(),
            "same_band": d["same_band"].to_numpy().astype(float),
            "same_city": d["same_city"].to_numpy(),
        }
    )
    raw = or_by_sender_sex(h2d, controls=False).set_index("sender_sex")
    adj = or_by_sender_sex(h2d, controls=True).set_index("sender_sex")
    n_send = h2d.groupby("sender_sex")["sender"].nunique()
    orows = []
    for s in SEXES:
        ns = int(n_send.get(s, 0))
        row = {"sender_sex": s, "n_senders": ns, "reportable": ns >= MIN_SENDERS_REPORT}
        for tag, tab in (("raw", raw), ("adj", adj)):
            if s in tab.index and ns >= MIN_CELL:
                r = tab.loc[s]
                row[f"or_{tag}"], row[f"lo_{tag}"], row[f"hi_{tag}"] = (
                    r["odds_ratio"],
                    r["ci_low"],
                    r["ci_high"],
                )
            else:
                row[f"or_{tag}"] = row[f"lo_{tag}"] = row[f"hi_{tag}"] = np.nan
        orows.append(row)
    odds = pd.DataFrame(orows)[
        [
            "sender_sex",
            "or_raw",
            "lo_raw",
            "hi_raw",
            "or_adj",
            "lo_adj",
            "hi_adj",
            "n_senders",
            "reportable",
        ]
    ]
    return {"matrix": matrix, "odds": odds}


# ------------------------------------------------------------------------- descriptives


def _share_table(series: pd.Series, name: str) -> pd.DataFrame:
    counts = series.fillna("unknown").astype(str).value_counts()
    total = counts.sum()
    out = pd.DataFrame(
        {
            "zmienna": name,
            "kategoria": counts.index,
            "odsetek": np.where(counts.to_numpy() < MIN_CELL, np.nan, counts.to_numpy() / total),
        }
    )
    return out


def descriptives(d: pd.DataFrame, flow: dict[str, int]) -> dict[str, pd.DataFrame]:
    """Sample flow, sender composition and the share of known lifestyle fields.

    - `flow`: krok, n_swipes (swipe steps from `flow`).
    - `sample`: zmienna, kategoria, odsetek for sender sex, age band and city (one row per
      sender; the first as-of row). Categories with fewer than 5 senders are suppressed.
    - `lifestyle_missing`: pole, odsetek_znanych_po_d13, odsetek_znanych_przed_d13, measured on
      receiver as-of profiles per swipe in the analysis sample, before and after filling empty
      structured fields from lifestyle tags (D13).

    The project documents quote 74-81% missing lifestyle fields. That figure refers to the raw
    structured columns of the user table (before D13 and over all users, including users who
    never swipe or are swiped). Here the base is *swipe receivers in the analysis sample*, as-of
    the swipe, so the shares differ; compare `przed_d13` with the documented figure and
    `po_d13` with the gain from tag imputation.
    """
    labels = {
        "swipes_profile_total": "wszystkie swipe'y na profile",
        "swipes_after_hyderabad": "po usunięciu Hyderabadu (D10)",
        "swipes_complete_case": "po complete-case (analiza)",
    }
    fl = pd.DataFrame(
        [{"krok": labels.get(k, k), "n_swipes": int(v)} for k, v in flow.items() if k in labels]
    )
    first = d.drop_duplicates("user_key")
    sample = pd.concat(
        [
            _share_table(first["sex_sender"], "plec_nadawcy"),
            _share_table(first["age_band_sender"], "wiek_nadawcy"),
            _share_table(first["city_sender"], "miasto_nadawcy"),
        ],
        ignore_index=True,
    )
    rows = []
    for f in h1mod.LIFESTYLE_STRUCTURED_FIELDS:
        if f"rcv_known_after_{f}" not in d:
            continue
        rows.append(
            {
                "pole": f,
                "odsetek_znanych_po_d13": float(d[f"rcv_known_after_{f}"].mean()),
                "odsetek_znanych_przed_d13": float(d[f"rcv_known_raw_{f}"].mean()),
            }
        )
    return {"flow": fl, "sample": sample, "lifestyle_missing": pd.DataFrame(rows)}


# -------------------------------------------------------------------------------- run_all


def _cache_key(params: dict, n_rows: int) -> str:
    src = Path(__file__).read_bytes()
    payload = repr(sorted(params.items())) + f"|rows={n_rows}|src={hashlib.sha256(src).hexdigest()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def run_all(
    n_boot: int = 1000,
    n_perm: int = 200,
    fast: bool = False,
    cache_dir: str | Path | None = "data/interim/unified/cache",
    n_cv_seeds: int = 3,
    d: pd.DataFrame | None = None,
    flow: dict[str, int] | None = None,
    data_dir: str | Path = "data/interim/unified",
    docs_dir: str | Path = "docs",
) -> dict[str, object]:
    """Whole analysis. `fast=True` uses n_boot=100, n_perm=10 (a few minutes at most).

    Returns a dict:
    - `compare_pair`, `compare_receiver`: output of `compare_blocks` for both variants;
    - `sensitivity`: long DataFrame (pair variant);
    - `sex_summary`: dict(matrix, odds);
    - `descriptives`: dict(flow, sample, lifestyle_missing);
    - `meta`: dict with parameters, n_rows and per-step timings in seconds.

    The result (aggregates only, no rows) is cached under `cache_dir` keyed by the parameters,
    the row count and a hash of this source file; pass `cache_dir=None` to disable.
    """
    if fast:
        n_boot, n_perm = 100, 10
    t0 = time.perf_counter()
    if d is None:
        d, flow = build_unified_table(data_dir, docs_dir)
    flow = flow or {}
    params = {"n_boot": n_boot, "n_perm": n_perm, "n_cv_seeds": n_cv_seeds}
    path = None
    if cache_dir is not None:
        path = Path(cache_dir) / f"run_all_{_cache_key(params, len(d))}.pkl"
        if path.exists():
            with path.open("rb") as fh:
                return pickle.load(fh)

    timing = {"build_table": time.perf_counter() - t0}

    def step(name: str, fn):
        t = time.perf_counter()
        r = fn()
        timing[name] = time.perf_counter() - t
        return r

    out: dict[str, object] = {
        "compare_pair": step(
            "compare_pair",
            lambda: compare_blocks(d, n_boot, n_perm, n_cv_seeds=n_cv_seeds, variant="pair"),
        ),
        "compare_receiver": step(
            "compare_receiver",
            lambda: compare_blocks(
                d, n_boot, n_perm, n_cv_seeds=n_cv_seeds, variant="pair+receiver"
            ),
        ),
        "sensitivity": step("sensitivity", lambda: sensitivity(d, n_boot=min(n_boot, 300))),
        "sex_summary": step("sex_summary", lambda: sex_summary(d, n_boot=n_boot)),
        "descriptives": step("descriptives", lambda: descriptives(d, flow)),
    }
    timing["total"] = time.perf_counter() - t0
    out["meta"] = {**params, "n_rows": len(d), "timing_s": timing, "fast": fast}
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(out, fh)
    return out
