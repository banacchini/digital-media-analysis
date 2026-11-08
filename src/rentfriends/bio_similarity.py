"""Do users with similar bios match more often? Embedding cosine similarity vs. swipe outcomes.

Input: unit-length bio embeddings from `embed_bios` and the swipe table from `h2.build_swipe_table`.
Only vectors, ids and bio lengths are used; no bio text is read here.

Two outcomes (codebook: match = both swiped right, only pairs with both swipes recorded):

- pair level (secondary outcome, `match`): unordered pair {A, B}, both directions observed;
- directed level (`y_right`): swipe A -> B, which is where "likes people who write like me" lives.

Models are logistic with two-way clustered standard errors (the same user sits in many pairs).
The effect is the odds ratio per 1 SD of cosine similarity. Controls: same sex, age band
difference, same band, same city, and both bios' log length (embeddings carry length and
language/style, so similarity alone is confounded with how much and how people write).

Null baseline: bio vectors are shuffled across users (one vector per user stays intact), the
similarity is recomputed, and the crude log OR is re-estimated. A real effect should sit outside
that null; a negative result is a result.

Everything here is exploratory until H-bio is pre-registered in the M1 card.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

SEED = 20261108


# ------------------------------------------------------------------------- similarity


@dataclass
class BioEmbeddings:
    vectors: np.ndarray  # (n, dim), unit length
    keys: pd.DataFrame  # `user_key`, `bio_len`, aligned with `vectors`

    def index(self) -> pd.Series:
        return pd.Series(np.arange(len(self.keys)), index=self.keys["user_key"].to_numpy())


def attach_similarity(swipes: pd.DataFrame, emb: BioEmbeddings) -> pd.DataFrame:
    """Keep swipes where both users have a bio vector; add `bio_sim`, `s_loglen`, `r_loglen`.

    Also adds `i_s`, `i_r` (row indexes into `emb.vectors`) for the permutation null.
    """
    idx = emb.index()
    d = swipes.copy()
    d["i_s"] = d["sender"].map(idx)
    d["i_r"] = d["receiver"].map(idx)
    d = d.dropna(subset=["i_s", "i_r"]).copy()
    d["i_s"] = d["i_s"].astype(int)
    d["i_r"] = d["i_r"].astype(int)
    d["bio_sim"] = pairwise_cosine(emb.vectors, d["i_s"].to_numpy(), d["i_r"].to_numpy())
    loglen = np.log1p(emb.keys["bio_len"].to_numpy().astype(float))
    d["s_loglen"] = loglen[d["i_s"].to_numpy()]
    d["r_loglen"] = loglen[d["i_r"].to_numpy()]
    return d.reset_index(drop=True)


def pairwise_cosine(
    vecs: np.ndarray, i: np.ndarray, j: np.ndarray, chunk: int = 200_000
) -> np.ndarray:
    """Row-wise dot products of unit vectors `vecs[i]` and `vecs[j]` (cosine similarity)."""
    out = np.empty(len(i), dtype=np.float64)
    for s in range(0, len(i), chunk):
        sl = slice(s, s + chunk)
        out[sl] = np.einsum("ij,ij->i", vecs[i[sl]], vecs[j[sl]])
    return out


def zscore(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else x - x.mean()


# ------------------------------------------------------------------------- pair table


def build_pair_table(d: pd.DataFrame) -> pd.DataFrame:
    """One row per unordered pair where both directed swipes exist.

    `d` is the output of `attach_similarity`. Duplicate directed swipes keep the earliest one.
    `match` = 1 if both swiped right. Pair controls are symmetric: same_sex, abs age band
    difference, same_band, same_city. Row order is user `a` < user `b`.
    """
    d = d.sort_values("day").drop_duplicates(["sender", "receiver"], keep="first")
    rev = d[["sender", "receiver", "y_right"]].rename(
        columns={"sender": "receiver", "receiver": "sender", "y_right": "y_back"}
    )
    p = d.merge(rev, on=["sender", "receiver"], how="inner")
    p = p[p["sender"].astype(str) < p["receiver"].astype(str)].copy()
    p["match"] = ((p["y_right"] == 1) & (p["y_back"] == 1)).astype(int)
    p["abs_age_band_diff"] = p["age_band_diff"].abs()
    p = p.rename(columns={"sender": "a", "receiver": "b"})
    keep = [
        "a",
        "b",
        "match",
        "bio_sim",
        "s_loglen",
        "r_loglen",
        "same_sex",
        "abs_age_band_diff",
        "same_band",
        "same_city",
        "i_s",
        "i_r",
    ]
    return p[keep].reset_index(drop=True)


# ------------------------------------------------------------------------- models


def _design(d: pd.DataFrame, controls: bool, abs_age: bool) -> pd.DataFrame:
    X = pd.DataFrame({"bio_sim_z": zscore(d["bio_sim"].to_numpy())}, index=d.index)
    if controls:
        X["same_sex"] = d["same_sex"].to_numpy()
        X["age_diff"] = d["abs_age_band_diff" if abs_age else "age_band_diff"].abs().to_numpy()
        X["same_band"] = d["same_band"].to_numpy()
        for lev in ("same", "different"):  # reference: unknown
            X[f"city_{lev}"] = (d["same_city"] == lev).to_numpy().astype(float)
        X["loglen_min"] = np.minimum(d["s_loglen"], d["r_loglen"]).to_numpy()
        X["loglen_max"] = np.maximum(d["s_loglen"], d["r_loglen"]).to_numpy()
    return sm.add_constant(X, prepend=True)


def similarity_or(
    d: pd.DataFrame,
    outcome: str,
    group_cols: tuple[str, str],
    *,
    controls: bool = True,
    level: float = 0.95,
) -> dict:
    """Odds ratio per 1 SD of bio similarity with two-way clustered CI.

    `outcome` is `y_right` (directed table, groups sender/receiver) or `match` (pair table,
    groups a/b). Rows with missing controls are dropped when `controls=True`.
    """
    need = ["bio_sim", outcome]
    if controls:
        need += ["same_sex", "same_band", "s_loglen", "r_loglen"]
        need += ["abs_age_band_diff"] if outcome == "match" else ["age_band_diff"]
    d = d.dropna(subset=need)
    X = _design(d, controls, abs_age=outcome == "match")
    y = d[outcome].to_numpy()
    # users appear on both sides, so factorise one shared id space for the two cluster columns
    codes, _ = pd.factorize(pd.concat([d[group_cols[0]], d[group_cols[1]]]))
    groups = np.column_stack([codes[: len(d)], codes[len(d) :]])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.Logit(y, X)
        try:
            res = model.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
            cluster = "two-way"
        except Exception:
            res = model.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups[:, 0]})
            cluster = "first-column"
    b, se = res.params["bio_sim_z"], res.bse["bio_sim_z"]
    z = norm.ppf(0.5 + level / 2)
    return {
        "outcome": outcome,
        "controls": controls,
        "n": len(d),
        "n_users": int(pd.unique(np.concatenate([d[group_cols[0]], d[group_cols[1]]])).size),
        "base_rate": float(y.mean()),
        "odds_ratio_per_sd": float(np.exp(b)),
        "ci_low": float(np.exp(b - z * se)),
        "ci_high": float(np.exp(b + z * se)),
        "p_value": float(2 * norm.sf(abs(b / se))),
        "cluster": cluster,
    }


def within_sender_effect(d: pd.DataFrame, level: float = 0.95) -> dict:
    """Robustness: does a sender swipe right more on bios closer to their own?

    Linear probability model of `y_right` on bio similarity, both demeaned within sender
    (sender fixed effect), SE clustered on sender. Absorbs each sender's generosity, so it
    compares targets of the same sender only. The slope is the change in P(right) per 1 SD of
    similarity (SD computed within the sample).
    """
    d = d.dropna(subset=["bio_sim", "y_right"]).copy()
    d["sim_z"] = zscore(d["bio_sim"].to_numpy())
    g = d.groupby("sender")
    x = d["sim_z"] - g["sim_z"].transform("mean")
    y = d["y_right"] - g["y_right"].transform("mean")
    keep = g["y_right"].transform("size") > 1
    x, y = x[keep], y[keep]
    groups = pd.factorize(d.loc[keep, "sender"])[0]
    res = sm.OLS(y.to_numpy(), x.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": groups})
    b, se = float(res.params[0]), float(res.bse[0])
    z = norm.ppf(0.5 + level / 2)
    return {
        "n": int(keep.sum()),
        "n_senders": int(pd.unique(groups).size),
        "dP_per_sd": b,
        "ci_low": b - z * se,
        "ci_high": b + z * se,
        "p_value": float(2 * norm.sf(abs(b / se))) if se > 0 else float("nan"),
    }


def rate_by_similarity_bin(d: pd.DataFrame, outcome: str, q: int = 5, level: float = 0.95):
    """Outcome rate per similarity quantile (Wilson CI ignores clustering: too narrow)."""
    from rentfriends.h2 import wilson_interval

    d = d.dropna(subset=["bio_sim", outcome]).copy()
    d["bin"] = pd.qcut(d["bio_sim"], q, labels=False, duplicates="drop")
    rows = []
    for b, g in d.groupby("bin"):
        k, n = float(g[outcome].sum()), len(g)
        lo, hi = wilson_interval(k, n, level)
        rows.append((int(b), n, g["bio_sim"].mean(), k / n, lo, hi))
    return pd.DataFrame(rows, columns=["bin", "n", "mean_sim", "rate", "wilson_low", "wilson_high"])


# ------------------------------------------------------------------- null baseline


def _log_or_slope(x: np.ndarray, y: np.ndarray, iters: int = 25) -> float:
    """Slope of a univariate logistic regression (IRLS), x already standardised."""
    X = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        w = np.maximum(p * (1 - p), 1e-9)
        step = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (y - p))
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return float(beta[1])


def permutation_null(
    d: pd.DataFrame,
    emb: BioEmbeddings,
    outcome: str,
    n_perm: int = 200,
    seed: int = SEED,
) -> tuple[float, np.ndarray]:
    """Crude log OR per 1 SD of similarity, and its null from shuffling vectors across users.

    Each user keeps one intact bio vector but gets another user's, so the pair similarity
    distribution is realistic while any link to the outcome is broken. Returns
    (observed, null of length n_perm). No controls, so compare with the crude (uncontrolled) OR.
    """
    y = d[outcome].to_numpy().astype(float)
    i, j = d["i_s"].to_numpy(), d["i_r"].to_numpy()
    observed = _log_or_slope(zscore(pairwise_cosine(emb.vectors, i, j)), y)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for k in range(n_perm):
        perm = rng.permutation(len(emb.vectors))
        null[k] = _log_or_slope(zscore(pairwise_cosine(emb.vectors, perm[i], perm[j])), y)
    return observed, null


def permutation_p(observed: float, null: np.ndarray) -> float:
    """Two-sided permutation p-value with the +1 correction."""
    return float((1 + np.sum(np.abs(null) >= abs(observed))) / (1 + len(null)))


# ------------------------------------------------------------------------------ CLI


def run(data_dir, interim_dir, n_perm: int = 200) -> pd.DataFrame:
    """Full analysis on real data; returns an aggregated summary (no row-level output)."""
    from rentfriends import h2

    swipes = h2.build_swipe_table(h2.load_tables(data_dir))
    swipes = swipes[~swipes["sender_extreme"]]  # G10: drop all-right / all-left accounts
    emb = BioEmbeddings(
        vectors=np.load(interim_dir / "bio_embeddings.npy"),
        keys=pd.read_parquet(interim_dir / "bio_embeddings_keys.parquet"),
    )
    directed = attach_similarity(swipes, emb)
    pairs = build_pair_table(directed)

    rows = []
    for name, tab, outcome, grp in (
        ("directed", directed, "y_right", ("sender", "receiver")),
        ("pair", pairs, "match", ("a", "b")),
    ):
        for controls in (False, True):
            rows.append({"level": name, **similarity_or(tab, outcome, grp, controls=controls)})
        obs, null = permutation_null(tab, emb, outcome, n_perm=n_perm)
        rows.append(
            {
                "level": name,
                "outcome": outcome,
                "controls": "null",
                "n": len(tab),
                "odds_ratio_per_sd": float(np.exp(obs)),
                "ci_low": float(np.exp(np.quantile(null, 0.025))),
                "ci_high": float(np.exp(np.quantile(null, 0.975))),
                "p_value": permutation_p(obs, null),
                "cluster": f"shuffled vectors, {n_perm} perms (CI = null 95% range)",
            }
        )
    ws = within_sender_effect(directed)
    rows.append({"level": "directed", "outcome": "y_right", "controls": "sender FE", **ws})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--data", type=Path, default=Path("data/processed"))
    p.add_argument("--interim", type=Path, default=Path("data/interim"))
    p.add_argument("--n-perm", type=int, default=200)
    p.add_argument("--out", type=Path, default=Path("data/interim/bio_similarity_summary.csv"))
    args = p.parse_args(argv)
    summary = run(args.data, args.interim, args.n_perm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out, index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
