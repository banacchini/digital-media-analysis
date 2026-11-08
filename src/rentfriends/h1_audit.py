"""H1 audit follow-up analyses (2026-11-08): age direction, block increments, bootstrap CIs, ...

Everything here works on the aggregate-level H1 analysis dataset; no `bio` field is used or
produced. Cells with fewer than `min_users` distinct senders are suppressed (G12).
"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import average_precision_score

from rentfriends.h1 import (
    H1Spec,
    _auc,
    _logloss,
    design_matrix,
    model_subsets,
    prepare_h1_sample,
    sender_folds,
)

AGE_BAND_LABELS = ("18-20", "21-23", "24-26", "27+")


def _sender_boot_index(n_senders: int, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_senders, size=(n_boot, n_senders))


def age_direction_check(
    df: pd.DataFrame,
    n_boot: int = 500,
    seed: int = 0,
    min_users: int = 5,
    level: float = 0.95,
) -> dict[str, pd.DataFrame]:
    """Is a receiver one band *younger* more likely to be accepted than the same band? (Z3)

    Returns three tables:
    - `cells`: right-swipe rate by sender band x signed band difference (small cells suppressed);
    - `contrast`: per sender band, rate(diff=-1) - rate(diff=0) with sender-cluster bootstrap CI.
      Only sender bands that can have younger targets appear (the 18-20 band cannot);
    - `pooled`: logit with sender-band fixed effects and dummies for the difference
      (reference: same band), SE clustered by sender.
    """
    d = df.dropna(subset=["age_band_diff", "age_band_sender", "y_right", "user_key"]).copy()
    d["diff"] = d["age_band_diff"].astype(int)

    cells = (
        d.groupby(["age_band_sender", "diff"])
        .agg(n=("y_right", "size"), k=("y_right", "sum"), n_users=("user_key", "nunique"))
        .reset_index()
        .rename(columns={"diff": "age_band_diff"})
    )
    cells["rate"] = np.where(cells["n_users"] >= min_users, cells["k"] / cells["n"], np.nan)
    cells.loc[cells["n_users"] < min_users, ["n", "k"]] = np.nan

    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for band in AGE_BAND_LABELS:
        sub = d[d["age_band_sender"] == band]
        same, younger = sub[sub["diff"] == 0], sub[sub["diff"] == -1]
        if len(younger) == 0 or len(same) == 0:
            continue
        senders, codes = np.unique(sub["user_key"].to_numpy(), return_inverse=True)
        n_s = len(senders)

        def counts(part: pd.DataFrame, senders: np.ndarray = senders, n_s: int = n_s):
            c = pd.Index(senders).get_indexer(part["user_key"])
            n = np.bincount(c, minlength=n_s).astype(float)
            k = np.bincount(c, weights=part["y_right"].to_numpy(), minlength=n_s)
            return n, k

        n0, k0 = counts(same)
        n1, k1 = counts(younger)
        idx = _sender_boot_index(n_s, n_boot, seed)
        with np.errstate(invalid="ignore", divide="ignore"):
            boot = k1[idx].sum(1) / n1[idx].sum(1) - k0[idx].sum(1) / n0[idx].sum(1)
        point = k1.sum() / n1.sum() - k0.sum() / n0.sum()
        lo, hi = np.nanquantile(boot, [lo_q, hi_q])
        rows.append(
            {
                "age_band_sender": band,
                "n_same": int(n0.sum()),
                "n_younger": int(n1.sum()),
                "n_users": int((n0 + n1 > 0).sum()),
                "rate_same": k0.sum() / n0.sum(),
                "rate_younger": k1.sum() / n1.sum(),
                "diff_younger_minus_same": point,
                "ci_low": lo,
                "ci_high": hi,
            }
        )
    contrast = pd.DataFrame(rows)
    return {"cells": cells, "contrast": contrast, "pooled": _pooled_direction_logit(d)}


def _pooled_direction_logit(d: pd.DataFrame) -> pd.DataFrame:
    terms = {
        "younger_by_2plus": d["diff"] <= -2,
        "younger_by_1": d["diff"] == -1,
        "older_by_1": d["diff"] == 1,
        "older_by_2plus": d["diff"] >= 2,
    }
    X = pd.DataFrame({k: v.astype(float) for k, v in terms.items()}, index=d.index)
    X = X.loc[:, X.sum() > 0]
    sband = pd.get_dummies(d["age_band_sender"], prefix="sband", dtype=float)
    X = pd.concat([X, sband.drop(columns=["sband_18-20"], errors="ignore")], axis=1)
    X = sm.add_constant(X)
    groups = pd.factorize(d["user_key"])[0]
    fit = sm.Logit(d["y_right"].to_numpy(), X).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": groups}
    )
    out = pd.DataFrame(
        {
            "term": fit.params.index,
            "coef": fit.params.values,
            "se": fit.bse.values,
            "or": np.exp(fit.params.values),
            "ci_low": np.exp(fit.params.values - 1.96 * fit.bse.values),
            "ci_high": np.exp(fit.params.values + 1.96 * fit.bse.values),
            "p_value": fit.pvalues.values,
        }
    )
    return out[out["term"].isin(terms)].reset_index(drop=True)


def block_increment_table(ll: dict[str, float], block_df: dict[str, int]) -> pd.DataFrame:
    """Increment of each block as first, as last and averaged over all orderings (Z4).

    `ll` maps model names (controls, age, interests, lifestyle, age_interests, age_lifestyle,
    interests_lifestyle, full) to their log-likelihoods; `block_df` gives the number of columns
    per block. The mean over the 6 orderings is the Shapley value, so the three block means add
    up to LL(full) - LL(controls). A composite row `age+interests` supports the card's
    criterion (lifestyle vs age+interests); its mean averages the 2 orderings of 2 players.
    Also reported: dLL per degree of freedom and dAIC = -2 dLL + 2 df (negative = block pays off).
    """
    blocks = ("age", "interests", "lifestyle")

    def name_of(members: frozenset[str]) -> str:
        if not members:
            return "controls"
        if len(members) == 3:
            return "full"
        return "_".join(b for b in blocks if b in members)

    def value(members: frozenset[str]) -> float:
        return ll[name_of(members)]

    rows = []
    for b in blocks:
        others = frozenset(blocks) - {b}
        first = value(frozenset({b})) - value(frozenset())
        last = value(frozenset(blocks)) - value(others)
        contribs = []
        for order in permutations(blocks):
            before = frozenset(order[: order.index(b)])
            contribs.append(value(before | {b}) - value(before))
        rows.append(_increment_row(b, block_df[b], first, last, float(np.mean(contribs))))

    ai = frozenset({"age", "interests"})
    life = frozenset({"lifestyle"})
    first = value(ai) - value(frozenset())
    last = value(frozenset(blocks)) - value(life)
    rows.append(
        _increment_row(
            "age+interests",
            block_df["age"] + block_df["interests"],
            first,
            last,
            (first + last) / 2,
        )
    )
    return pd.DataFrame(rows)


def _increment_row(name: str, df_b: int, first: float, last: float, mean: float) -> dict:
    row: dict[str, float | int | str] = {"block": name, "df": df_b}
    for tag, dll in (("first", first), ("last", last), ("mean", mean)):
        row[f"dll_{tag}"] = dll
        row[f"dll_{tag}_per_df"] = dll / df_b
        row[f"daic_{tag}"] = -2 * dll + 2 * df_b
    return row


def block_increments_from_fit(res: dict) -> pd.DataFrame:
    """`block_increment_table` for the models returned by `h1.fit_h1_logit_models`."""
    ll = {name: float(fit.llf) for name, fit in res["models"].items()}
    n_vars = res["summary"].set_index("model")["n_vars"]
    block_df = {
        "age": int(n_vars["age"] - n_vars["controls"]),
        "interests": int(n_vars["interests"] - n_vars["controls"]),
        "lifestyle": int(n_vars["lifestyle"] - n_vars["controls"]),
    }
    return block_increment_table(ll, block_df)


def fit_logit_fast(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray | None = None,
    beta0: np.ndarray | None = None,
    max_iter: int = 40,
    tol: float = 1e-9,
) -> tuple[np.ndarray, float]:
    """Weighted logistic regression by Newton-Raphson; returns (coefficients, weighted loglik).

    Integer weights equal row duplication, which is what a cluster bootstrap needs. A tiny ridge
    keeps the Hessian invertible when a resample empties a sparse dummy.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.ones(len(y)) if w is None else np.asarray(w, dtype=float)
    beta = np.zeros(X.shape[1]) if beta0 is None else np.array(beta0, dtype=float)
    ridge = 1e-8 * np.eye(X.shape[1])

    def loglik(b: np.ndarray) -> float:
        eta = X @ b
        return float(np.sum(w * (y * eta - np.logaddexp(0.0, eta))))

    ll = loglik(beta)
    for _ in range(max_iter):
        p = 1.0 / (1.0 + np.exp(-(X @ beta)))
        grad = X.T @ (w * (y - p))
        hess = (X * (w * p * (1 - p))[:, None]).T @ X + ridge
        step = np.linalg.solve(hess, grad)
        t = 1.0
        while True:  # step halving keeps the likelihood monotone
            new_ll = loglik(beta + t * step)
            if new_ll >= ll - 1e-12 or t < 1e-6:
                break
            t /= 2
        beta = beta + t * step
        converged = abs(new_ll - ll) < tol
        ll = new_ll
        if converged:
            break
    return beta, ll


def bootstrap_model_loglik(
    df: pd.DataFrame,
    cluster_col: str = "user_key",
    n_boot: int = 500,
    seed: int = 0,
    spec: H1Spec | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Log-likelihood of the 8 block models on cluster-bootstrap resamples (Z5).

    Clusters (senders or receivers) are drawn with replacement; a resample is represented by
    integer row weights, so every replicate refits all models on the same design matrices.
    Returns the observed log-likelihoods and an (n_boot x 8) frame of resampled ones.
    """
    spec = spec or H1Spec()
    d = prepare_h1_sample(df, spec)
    y = d["y_right"].to_numpy(dtype=float)
    designs = {
        name: design_matrix(d, spec, combo).to_numpy(dtype=float)
        for name, combo in model_subsets().items()
    }
    codes, uniques = pd.factorize(d[cluster_col])
    n_c = len(uniques)

    obs, betas = {}, {}
    for name, X in designs.items():
        betas[name], obs[name] = fit_logit_fast(X, y)

    idx = _sender_boot_index(n_c, n_boot, seed)
    out = np.empty((n_boot, len(designs)))
    for b in range(n_boot):
        mult = np.bincount(idx[b], minlength=n_c).astype(float)
        w = mult[codes]
        for j, (name, X) in enumerate(designs.items()):
            out[b, j] = fit_logit_fast(X, y, w, beta0=betas[name])[1]
    return pd.Series(obs), pd.DataFrame(out, columns=list(designs))


_CONTRASTS = {
    "lifestyle - age+interests": ("lifestyle", "age+interests"),
    "lifestyle - interests": ("lifestyle", "interests"),
    "lifestyle - age": ("lifestyle", "age"),
}


def summarise_block_differences(
    obs: pd.Series,
    boot: pd.DataFrame,
    block_df: dict[str, int],
    level: float = 0.95,
) -> pd.DataFrame:
    """Percentile CIs for differences of block increments (the card's H1 criterion).

    For each definition of the increment (`first`, `last`, `mean`) and each contrast
    (lifestyle minus age+interests / interests / age) report the observed difference in dLL,
    the bootstrap percentile CI and the share of resamples with a positive difference.
    """
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2

    def increments(ll: pd.Series) -> pd.DataFrame:
        return block_increment_table(ll.to_dict(), block_df).set_index("block")

    obs_tbl = increments(obs)
    boot_tbls = [increments(boot.iloc[i]) for i in range(len(boot))]
    rows = []
    for definition in ("first", "last", "mean"):
        col = f"dll_{definition}"
        for contrast, (lhs, rhs) in _CONTRASTS.items():
            est = obs_tbl.loc[lhs, col] - obs_tbl.loc[rhs, col]
            reps = np.array([t.loc[lhs, col] - t.loc[rhs, col] for t in boot_tbls])
            rows.append(
                {
                    "definition": definition,
                    "contrast": contrast,
                    "estimate": est,
                    "ci_low": float(np.quantile(reps, lo_q)),
                    "ci_high": float(np.quantile(reps, hi_q)),
                    "boot_se": float(reps.std(ddof=1)),
                    "share_positive": float((reps > 0).mean()),
                }
            )
    return pd.DataFrame(rows)


def combine_cluster_cis(by_sender: pd.DataFrame, by_receiver: pd.DataFrame) -> pd.DataFrame:
    """Merge sender- and receiver-clustered bootstrap tables; the wider CI is conservative."""
    keys = ["definition", "contrast"]
    s = by_sender.set_index(keys)
    r = by_receiver.set_index(keys)
    out = pd.DataFrame(index=s.index)
    out["estimate"] = s["estimate"]
    for tag, tbl in (("sender", s), ("receiver", r)):
        out[f"ci_low_{tag}"] = tbl["ci_low"]
        out[f"ci_high_{tag}"] = tbl["ci_high"]
    width_s = s["ci_high"] - s["ci_low"]
    width_r = r["ci_high"] - r["ci_low"]
    receiver_wider = width_r > width_s
    out["ci_low_conservative"] = np.where(receiver_wider, r["ci_low"], s["ci_low"])
    out["ci_high_conservative"] = np.where(receiver_wider, r["ci_high"], s["ci_high"])
    out["wider_is"] = np.where(receiver_wider, "receiver", "sender")
    out["excludes_zero_conservative"] = (out["ci_low_conservative"] > 0) | (
        out["ci_high_conservative"] < 0
    )
    return out.reset_index()


def oof_predictions(
    df: pd.DataFrame, n_splits: int = 5, seed: int = 0, spec: H1Spec | None = None
) -> pd.DataFrame:
    """Out-of-fold predicted probabilities of all block models, folds grouped by sender (Z5)."""
    spec = spec or H1Spec()
    d = prepare_h1_sample(df, spec)
    folds = sender_folds(d, n_splits, seed)
    y = d["y_right"].to_numpy(dtype=float)
    out = pd.DataFrame(
        {"y": y, "sender": pd.factorize(d["user_key"])[0], "fold": folds}, index=d.index
    )
    for name, combo in model_subsets().items():
        X = design_matrix(d, spec, combo).to_numpy(dtype=float)
        p = np.empty(len(d))
        for k in range(n_splits):
            tr, te = folds != k, folds == k
            beta, _ = fit_logit_fast(X[tr], y[tr])
            p[te] = 1.0 / (1.0 + np.exp(-(X[te] @ beta)))
        out[name] = p
    return out


def _cv_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "logloss": _logloss(y, p),
        "auc": _auc(y, p),
        "auc_pr": float(average_precision_score(y, p)),
    }


def _gain_contrasts(m: dict[str, dict[str, float]], metric: str) -> dict[tuple[str, str], float]:
    """Gains (positive = better) by definition and block, plus lifestyle-minus-X differences."""
    sign = -1.0 if metric == "logloss" else 1.0

    def g(model: str, ref: str) -> float:
        return sign * (m[model][metric] - m[ref][metric])

    first = {
        "lifestyle": g("lifestyle", "controls"),
        "age+interests": g("age_interests", "controls"),
        "interests": g("interests", "controls"),
        "age": g("age", "controls"),
    }
    last = {
        "lifestyle": g("full", "age_interests"),
        "age+interests": g("full", "lifestyle"),
        "interests": g("full", "age_lifestyle"),
        "age": g("full", "interests_lifestyle"),
    }
    out: dict[tuple[str, str], float] = {}
    for definition, gains in (("first", first), ("last", last)):
        for block, val in gains.items():
            out[(definition, f"gain: {block}")] = val
        for contrast, (lhs, rhs) in _CONTRASTS.items():
            out[(definition, contrast)] = gains[lhs] - gains[rhs]
    return out


def paired_cv_differences(
    oof: pd.DataFrame, n_boot: int = 500, seed: int = 0, level: float = 0.95
) -> pd.DataFrame:
    """Paired out-of-fold differences in logloss / AUC / AUC-PR with sender-bootstrap CIs (Z5).

    Positive values mean an improvement (for logloss: loss decreases). The bootstrap resamples
    senders and recomputes every model's pooled out-of-fold metric on the same resample, so the
    differences are paired. It is conditional on the fitted fold models (no refit).
    """
    models = list(model_subsets())
    y = oof["y"].to_numpy()
    P = {name: oof[name].to_numpy() for name in models}
    order = np.argsort(oof["sender"].to_numpy(), kind="stable")
    sender_sorted = oof["sender"].to_numpy()[order]
    cuts = np.flatnonzero(np.diff(sender_sorted)) + 1
    groups = np.split(order, cuts)

    def all_metrics(idx: np.ndarray | slice) -> dict[str, dict[str, float]]:
        return {name: _cv_metrics(y[idx], P[name][idx]) for name in models}

    obs = all_metrics(slice(None))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(groups), size=(n_boot, len(groups)))
    boot = []
    for b in range(n_boot):
        idx = np.concatenate([groups[i] for i in draws[b]])
        boot.append(all_metrics(idx))

    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for metric in ("logloss", "auc", "auc_pr"):
        est = _gain_contrasts(obs, metric)
        reps = [_gain_contrasts(m, metric) for m in boot]
        for key, value in est.items():
            vals = np.array([r[key] for r in reps])
            rows.append(
                {
                    "metric": metric,
                    "definition": key[0],
                    "contrast": key[1],
                    "estimate": value,
                    "ci_low": float(np.quantile(vals, lo_q)),
                    "ci_high": float(np.quantile(vals, hi_q)),
                }
            )
    return pd.DataFrame(rows)


def permute_within_strata(strata: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Index permutation that only moves items inside their own stratum (equal tag count)."""
    strata = np.asarray(strata)
    perm = np.arange(len(strata))
    for value in np.unique(strata):
        members = np.flatnonzero(strata == value)
        perm[members] = rng.permutation(members)
    return perm


def _set_matrix(sets: pd.Series, vocab: dict[str, int], weights: np.ndarray) -> np.ndarray:
    """Weighted indicator matrix (n x V): entry = tag weight if the swipe side has the tag."""
    m = np.zeros((len(sets), len(vocab)), dtype=np.float32)
    for i, tags in enumerate(sets):
        for t in tags:
            m[i, vocab[t]] = weights[vocab[t]]
    return m


def interests_permutation_baseline(
    df: pd.DataFrame,
    n_perm: int = 200,
    seed: int = 0,
    weights: dict[str, float] | None = None,
    n_boot: int = 500,
    level: float = 0.95,
) -> dict[str, object]:
    """Hobby overlap (Jaccard) of right vs left swipes against a permutation baseline (Z6b).

    The baseline reassigns receivers' hobby sets between swipes *within groups of equal tag
    count*, so the number of tags per receiver and the marginal tag distribution are preserved
    while the sender-receiver match is destroyed. With `weights` the IDF-weighted Jaccard is used.
    Reports observed means (sender-clustered bootstrap CI), the permutation distribution
    (mean and central `level` band) and a two-sided permutation p-value for right minus left.
    """
    d = df.dropna(subset=["y_right"]).reset_index(drop=True)
    vocab_list = sorted(
        {
            t
            for col in ("interests_set_sender", "interests_set_receiver")
            for tags in d[col]
            for t in tags
        }
    )
    vocab = {t: i for i, t in enumerate(vocab_list)}
    w = np.array([1.0 if weights is None else weights.get(t, 0.0) for t in vocab_list])
    S = _set_matrix(d["interests_set_sender"], vocab, w)
    R = _set_matrix(d["interests_set_receiver"], vocab, w)
    s_tot = S.sum(axis=1)
    r_tot = R.sum(axis=1)
    counts = d["interests_set_receiver"].map(len).to_numpy()
    y = d["y_right"].to_numpy().astype(bool)

    def jaccard(R_mat: np.ndarray, r_total: np.ndarray) -> np.ndarray:
        shared = np.minimum(S, R_mat).sum(axis=1)
        union = s_tot + r_total - shared
        return np.divide(shared, union, out=np.zeros_like(shared), where=union > 0)

    obs_j = jaccard(R, r_tot).astype(float)

    def group_means(j: np.ndarray) -> tuple[float, float]:
        return float(j[y].mean()), float(j[~y].mean())

    rng = np.random.default_rng(seed)
    perm_right, perm_left = np.empty(n_perm), np.empty(n_perm)
    for b in range(n_perm):
        p = permute_within_strata(counts, rng)
        perm_right[b], perm_left[b] = group_means(jaccard(R[p], r_tot[p]).astype(float))
    perm_diff = perm_right - perm_left

    obs_right, obs_left = group_means(obs_j)
    obs_diff = obs_right - obs_left
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2

    # sender-clustered bootstrap CI of the observed means
    codes, uniques = pd.factorize(d["user_key"])
    n_s = len(uniques)
    n_r = np.bincount(codes[y], minlength=n_s).astype(float)
    n_l = np.bincount(codes[~y], minlength=n_s).astype(float)
    sum_r = np.bincount(codes[y], weights=obs_j[y], minlength=n_s)
    sum_l = np.bincount(codes[~y], weights=obs_j[~y], minlength=n_s)
    idx = _sender_boot_index(n_s, n_boot, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        b_right = sum_r[idx].sum(1) / n_r[idx].sum(1)
        b_left = sum_l[idx].sum(1) / n_l[idx].sum(1)
    boots = {"right": b_right, "left": b_left, "right_minus_left": b_right - b_left}

    centre = perm_diff.mean()
    p_two = float((np.sum(np.abs(perm_diff - centre) >= abs(obs_diff - centre)) + 1) / (n_perm + 1))
    rows = []
    for group, obs, perm in (
        ("right", obs_right, perm_right),
        ("left", obs_left, perm_left),
        ("right_minus_left", obs_diff, perm_diff),
    ):
        rows.append(
            {
                "group": group,
                "observed": obs,
                "obs_ci_low": float(np.nanquantile(boots[group], lo_q)),
                "obs_ci_high": float(np.nanquantile(boots[group], hi_q)),
                "perm_mean": float(perm.mean()),
                "perm_lo": float(np.quantile(perm, lo_q)),
                "perm_hi": float(np.quantile(perm, hi_q)),
                "p_two_sided": p_two if group == "right_minus_left" else np.nan,
            }
        )
    return {
        "summary": pd.DataFrame(rows),
        "perm_right": perm_right,
        "perm_left": perm_left,
        "perm_diff": perm_diff,
        "n_swipes": len(d),
    }
