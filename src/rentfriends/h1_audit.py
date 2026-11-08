"""H1 audit follow-up analyses (2026-11-08): age direction, block increments, bootstrap CIs, ...

Everything here works on the aggregate-level H1 analysis dataset; no `bio` field is used or
produced. Cells with fewer than `min_users` distinct senders are suppressed (G12).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

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
