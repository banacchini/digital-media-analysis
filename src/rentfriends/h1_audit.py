"""H1 audit follow-up analyses (2026-11-08): age direction, block increments, bootstrap CIs, ...

Everything here works on the aggregate-level H1 analysis dataset; no `bio` field is used or
produced. Cells with fewer than `min_users` distinct senders are suppressed (G12).
"""

from __future__ import annotations

from itertools import permutations

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
