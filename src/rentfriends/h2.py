"""H2: sender and receiver demographics (sex, age band) versus the right swipe.

Implements the plan of the M1 card (decisions D4, D6-D10, D17, D18 in
`docs/prompts/m1-generation-plan.md`; variables in `docs/codebook.md`, part C):

- unit: directed swipe A -> B on a profile, outcome `y_right`;
- features come from the profile version valid on the swipe day (D7, as-of rule);
- Hyderabad accounts are dropped from the main analysis (D10);
- age bands 27+ are merged (D9); sex `O` is its own level (D8);
- H2 is an effect size: odds ratio (same vs different sex) by sender sex, with a CI that is
  clustered on sender and receiver (D17). The estimator is still `[DO POTWIERDZENIA]` (D18).

The sex matrix was seen before H2 was formalised, so every result here is exploratory.
Nothing in this module reads or prints bio text.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, rankdata

# Age bands in order. 27-30, 31-35 and 36+ are merged into one level (D9).
AGE_BANDS = ["18-20", "21-23", "24-26", "27-30", "31-35", "36+"]
AGE_INDEX = {"18-20": 0, "21-23": 1, "24-26": 2, "27-30": 3, "31-35": 3, "36+": 3}
SEXES = ["F", "M", "O"]
PROFILE_COLS = ["sex", "age_band", "city"]
HYDERABAD = "Hyderabad"
MIN_SWIPES_ACTIVE = 10  # sensitivity threshold from D6 / G10


# --------------------------------------------------------------------------- loading


@dataclass
class Tables:
    users: pd.DataFrame
    swipes: pd.DataFrame
    profile_history: pd.DataFrame


def load_tables(data_dir: Path) -> Tables:
    """Read the three parquet tables H2 needs from `data/processed/`."""
    return Tables(
        users=pd.read_parquet(data_dir / "users.parquet"),
        swipes=pd.read_parquet(data_dir / "swipes.parquet"),
        profile_history=pd.read_parquet(data_dir / "profile_history.parquet"),
    )


# ------------------------------------------------------------------ as-of profile (D7)


def asof_attributes(
    keys: pd.Series,
    days: pd.Series,
    users: pd.DataFrame,
    history: pd.DataFrame | None,
    cols: list[str] | None = None,
) -> pd.DataFrame:
    """Profile attributes of `keys` valid on `days`, plus a source flag (D7).

    1. swipe day later than the first version's day -> last version strictly before the swipe day
       (`prior_version`);
    2. swipe on the first version's day or earlier -> the oldest version v1 (`first_version`);
    3. user without history -> current `users` row (`users_current`).

    With `history=None` every row comes from `users` (the sensitivity version).
    """
    cols = cols or PROFILE_COLS
    out = pd.DataFrame(index=np.arange(len(keys)))
    current = users.drop_duplicates("user_key").set_index("user_key")[cols]
    cur = current.reindex(keys.to_numpy())
    for c in cols:
        out[c] = cur[c].to_numpy()
    out["source"] = "users_current"
    if history is None or history.empty:
        return out

    hist = history.sort_values(["day", "version"])[["user_key", "day", *cols]].copy()
    hist["_hday"] = hist["day"]
    # merge_asof needs identical key dtypes; parquet may store ids as "string" or "str"
    hist["user_key"] = hist["user_key"].astype(object)

    # first version per user (rule 2)
    first = (
        history.sort_values(["user_key", "version"]).groupby("user_key", sort=False).first()[cols]
    )
    fcur = first.reindex(keys.to_numpy())
    has_first = keys.isin(first.index).to_numpy()
    for c in cols:
        out[c] = np.where(has_first, fcur[c].to_numpy(), out[c])
    out.loc[has_first, "source"] = "first_version"

    # last version strictly before the swipe day (rule 1)
    q = pd.DataFrame(
        {
            "user_key": keys.to_numpy(),
            "day": days.to_numpy().astype("int64"),
            "_i": np.arange(len(keys)),
        }
    ).sort_values("day")
    q["user_key"] = q["user_key"].astype(object)
    hist["day"] = hist["day"].astype("int64")
    prior = pd.merge_asof(
        q, hist, on="day", by="user_key", allow_exact_matches=False, direction="backward"
    ).sort_values("_i")
    has_prior = prior["_hday"].notna().to_numpy()
    for c in cols:
        out[c] = np.where(has_prior, prior[c].to_numpy(), out[c])
    out.loc[has_prior, "source"] = "prior_version"
    return out


# ------------------------------------------------------------------- swipe-level table


def build_swipe_table(
    tables: Tables,
    *,
    feature_version: str = "asof",
    drop_hyderabad: bool = True,
) -> pd.DataFrame:
    """One row per directed profile swipe with sender/receiver features and H2 variables.

    `feature_version`: `"asof"` (main, D7) or `"users"` (sensitivity, current profile).
    """
    if feature_version not in ("asof", "users"):
        raise ValueError("feature_version must be 'asof' or 'users'")
    users, history = tables.users, tables.profile_history
    s = tables.swipes
    s = s[(s["target_type"] == "profile") & s["target_user_key"].notna()].copy()
    s = s[s["user_key"] != s["target_user_key"]]
    if drop_hyderabad:
        bad = set(users.loc[users["city"] == HYDERABAD, "user_key"])
        s = s[~s["user_key"].isin(bad) & ~s["target_user_key"].isin(bad)]
    s = s.reset_index(drop=True)

    hist = history if feature_version == "asof" else None
    snd = asof_attributes(s["user_key"], s["day"], users, hist)
    rcv = asof_attributes(s["target_user_key"], s["day"], users, hist)

    df = pd.DataFrame(
        {
            "sender": s["user_key"].to_numpy(),
            "receiver": s["target_user_key"].to_numpy(),
            "day": s["day"].to_numpy(),
            "y_right": (s["direction"] == "right").astype(int).to_numpy(),
            "sender_sex": snd["sex"].to_numpy(),
            "receiver_sex": rcv["sex"].to_numpy(),
            "sender_band": snd["age_band"].to_numpy(),
            "receiver_band": rcv["age_band"].to_numpy(),
            "sender_city": snd["city"].to_numpy(),
            "receiver_city": rcv["city"].to_numpy(),
        }
    )
    # pair-level source flag: prior_version only if both sides are; users_current if either is
    both_prior = (snd["source"] == "prior_version") & (rcv["source"] == "prior_version")
    any_cur = (snd["source"] == "users_current") | (rcv["source"] == "users_current")
    df["asof_source"] = np.where(
        both_prior, "prior_version", np.where(any_cur, "users_current", "first_version")
    )
    if feature_version == "users":
        df["asof_source"] = "users_current"
    return add_demography(flag_extreme_senders(df))


def flag_extreme_senders(df: pd.DataFrame) -> pd.DataFrame:
    """Add sender activity and an extreme-account flag (G10: all right or all left, n >= 10)."""
    g = df.groupby("sender")["y_right"].agg(["size", "mean"])
    extreme = (g["size"] >= MIN_SWIPES_ACTIVE) & g["mean"].isin([0.0, 1.0])
    df = df.copy()
    df["sender_n"] = df["sender"].map(g["size"])
    df["sender_extreme"] = df["sender"].map(extreme).astype(bool)
    return df


def add_demography(df: pd.DataFrame) -> pd.DataFrame:
    """Codebook part C variables: same_sex, sex_pair, age_band_diff, same_band, same_city."""
    df = df.copy()
    ok_sex = df["sender_sex"].isin(SEXES) & df["receiver_sex"].isin(SEXES)
    df["same_sex"] = np.where(
        ok_sex, (df["sender_sex"] == df["receiver_sex"]).astype(float), np.nan
    )
    df["sex_pair"] = np.where(ok_sex, df["sender_sex"] + ">" + df["receiver_sex"], None)
    s_idx = df["sender_band"].map(AGE_INDEX)
    r_idx = df["receiver_band"].map(AGE_INDEX)
    df["age_band_diff"] = (r_idx - s_idx).astype(float)  # receiver - sender, signed
    df["same_band"] = np.where(
        s_idx.notna() & r_idx.notna(), (s_idx == r_idx).astype(float), np.nan
    )

    def city_rel(a: str | None, b: str | None) -> str:
        if a is None or b is None or pd.isna(a) or pd.isna(b) or a == "inne" or b == "inne":
            return "unknown"
        return "same" if a == b else "different"

    df["same_city"] = [
        city_rel(a, b) for a, b in zip(df["sender_city"], df["receiver_city"], strict=True)
    ]
    return df


# ----------------------------------------------------------------- descriptive matrix


def wilson_interval(k: float, n: float, level: float = 0.95) -> tuple[float, float]:
    """Wilson CI for a proportion. Ignores clustering, so it is too narrow; use for reference."""
    if n == 0:
        return (np.nan, np.nan)
    z = norm.ppf(0.5 + level / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


def rate_matrix(
    df: pd.DataFrame, n_boot: int = 1000, seed: int = 0, level: float = 0.95
) -> pd.DataFrame:
    """P(right) per sender-sex x receiver-sex cell with a sender-cluster bootstrap CI.

    Returns a long table: sender_sex, receiver_sex, n, k, rate, ci_low, ci_high, wilson_low,
    wilson_high. The bootstrap resamples whole senders, so repeated swipes by one user are
    not treated as independent.
    """
    d = df[df["sex_pair"].notna()]
    senders = d["sender"].astype("category")
    s_codes = senders.cat.codes.to_numpy()
    n_s = len(senders.cat.categories)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_s, size=(n_boot, n_s))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for a in SEXES:
        for b in SEXES:
            m = ((d["sender_sex"] == a) & (d["receiver_sex"] == b)).to_numpy()
            n_c = np.bincount(s_codes[m], minlength=n_s).astype(float)
            k_c = np.bincount(s_codes[m], weights=d["y_right"].to_numpy()[m], minlength=n_s)
            n, k = n_c.sum(), k_c.sum()
            if n == 0:
                rows.append((a, b, 0, 0, np.nan, np.nan, np.nan, np.nan, np.nan))
                continue
            with np.errstate(invalid="ignore", divide="ignore"):
                boot = k_c[idx].sum(1) / n_c[idx].sum(1)
            lo, hi = np.nanquantile(boot, [lo_q, hi_q])
            wl, wh = wilson_interval(k, n, level)
            rows.append((a, b, int(n), int(k), k / n, lo, hi, wl, wh))
    return pd.DataFrame(
        rows,
        columns=[
            "sender_sex",
            "receiver_sex",
            "n",
            "k",
            "rate",
            "ci_low",
            "ci_high",
            "wilson_low",
            "wilson_high",
        ],
    )


# ---------------------------------------------------------- odds ratio by sender sex (D17)


def _cluster_groups(d: pd.DataFrame) -> np.ndarray:
    """Two-way cluster ids: sender and receiver (the same user may appear on both sides)."""
    return np.column_stack(
        [
            pd.factorize(d["sender"])[0],
            pd.factorize(d["receiver"])[0],
        ]
    )


def or_by_sender_sex(
    df: pd.DataFrame, *, controls: bool = False, level: float = 0.95
) -> pd.DataFrame:
    """Odds ratio (same sex vs different sex) of a right swipe, separately for each sender sex.

    Logit with a free intercept and a free `same_sex` slope per sender sex. Standard errors are
    clustered on sender and receiver (two-way). With `controls=True` the model adds
    `age_band_diff`, `same_band` and the same_city levels, so the OR becomes conditional on them.

    Returns one row per sender sex with enough variation: n, n_senders, raw P(right) for same and
    different sex, OR, CI, and the p-value of log OR = 0.
    """
    need = ["same_sex", "y_right"] + (["age_band_diff", "same_band"] if controls else [])
    d = df.dropna(subset=need)
    d = d[d["sender_sex"].isin(SEXES)]
    groups = _cluster_groups(d)

    cols, names = [], []
    for g in SEXES:
        m = (d["sender_sex"] == g).to_numpy()
        # need both same and different sex swipes to identify the slope
        if m.sum() == 0 or d.loc[m, "same_sex"].nunique() < 2:
            continue
        cols.append(m.astype(float))
        names.append(f"base[{g}]")
        cols.append(m * d["same_sex"].to_numpy())
        names.append(f"same[{g}]")
    if not names:
        return pd.DataFrame()
    if controls:
        cols += [d["age_band_diff"].to_numpy(), d["same_band"].to_numpy()]
        names += ["age_band_diff", "same_band"]
        for lev in ("same", "different"):  # reference: unknown
            cols.append((d["same_city"] == lev).to_numpy().astype(float))
            names.append(f"city_{lev}")
    X = pd.DataFrame(np.column_stack(cols), columns=names, index=d.index)
    y = d["y_right"].to_numpy()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.Logit(y, X)
        try:
            res = model.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
            cluster = "sender+receiver"
        except Exception:  # singular two-way covariance: fall back to sender only
            res = model.fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups[:, 0]})
            cluster = "sender"
    z = norm.ppf(0.5 + level / 2)
    rows = []
    for g in SEXES:
        name = f"same[{g}]"
        if name not in res.params.index:
            continue
        b, se = res.params[name], res.bse[name]
        m = d["sender_sex"] == g
        same = d.loc[m & (d["same_sex"] == 1), "y_right"]
        diff = d.loc[m & (d["same_sex"] == 0), "y_right"]
        rows.append(
            {
                "sender_sex": g,
                "n": int(m.sum()),
                "n_senders": int(d.loc[m, "sender"].nunique()),
                "p_right_same": same.mean(),
                "p_right_diff": diff.mean(),
                "odds_ratio": float(np.exp(b)),
                "ci_low": float(np.exp(b - z * se)),
                "ci_high": float(np.exp(b + z * se)),
                "p_value": float(2 * norm.sf(abs(b / se))),
                "cluster": cluster,
                "controls": controls,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- null baseline


def permutation_null_or(
    df: pd.DataFrame, sender_sex: str, n_perm: int = 1000, seed: int = 0
) -> tuple[float, np.ndarray]:
    """Observed log OR (same vs different sex) and its null from shuffled receiver sex.

    The shuffle permutes sex labels across receiver *users* (one label per receiver, its most
    common one), so each receiver keeps all of its swipes and popularity. This breaks any link
    between receiver sex and the outcome while keeping sender behaviour and the sex mix.
    Uses the crude 2x2 log OR (no controls). Returns (observed, null array of length n_perm).
    """
    d = df[(df["sender_sex"] == sender_sex) & df["same_sex"].notna()]
    recv_codes, recv_keys = pd.factorize(d["receiver"])
    mode_sex = (
        d.groupby("receiver")["receiver_sex"]
        .agg(lambda s: s.value_counts().index[0])
        .reindex(recv_keys)
    )
    sex_codes = mode_sex.map({s: i for i, s in enumerate(SEXES)}).to_numpy()
    y = d["y_right"].to_numpy()

    def log_or(same: np.ndarray) -> float:
        a = y[same].sum() + 0.5
        b = (~(y[same] == 1)).sum() + 0.5
        c = y[~same].sum() + 0.5
        e = (~(y[~same] == 1)).sum() + 0.5
        return float(np.log(a * e / (b * c)))

    # the observed value uses the real per-swipe receiver sex, as in the main model
    observed = log_or(d["same_sex"].to_numpy() == 1)
    rng = np.random.default_rng(seed)
    s_sex = d["sender_sex"].map({s: i for i, s in enumerate(SEXES)}).to_numpy()
    null = np.empty(n_perm)
    for i in range(n_perm):
        perm = rng.permutation(sex_codes)
        null[i] = log_or(s_sex == perm[recv_codes])
    return observed, null


# ---------------------------------------------------------------- user-grouped CV (D18)


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


def _design(d: pd.DataFrame, block: str) -> np.ndarray:
    """Design matrix for a feature block: sex pair dummies (+ age terms)."""
    cols = [np.ones(len(d))]
    if block in ("sex", "sex+age"):
        for pair in sorted({f"{a}>{b}" for a in SEXES for b in SEXES} - {"F>F"}):
            cols.append((d["sex_pair"] == pair).to_numpy().astype(float))
    if block == "sex+age":
        cols += [d["age_band_diff"].to_numpy(), d["same_band"].to_numpy()]
    return np.column_stack(cols)


def grouped_cv(df: pd.DataFrame, n_splits: int = 5, seed: int = 0) -> pd.DataFrame:
    """Out-of-sample log loss and AUC of nested demography blocks, with folds grouped by sender.

    Blocks: `null` (intercept), `sex` (sex-pair dummies), `sex+age` (adds band diff and same band).
    Folds split *senders*; a receiver can still appear in train and test, so this controls
    sender leakage only. Reported per fold so that the spread is visible.
    """
    d = df.dropna(subset=["sex_pair", "age_band_diff", "same_band"]).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    senders = d["sender"].unique()
    fold_of = dict(zip(senders, rng.permutation(len(senders)) % n_splits, strict=True))
    folds = d["sender"].map(fold_of).to_numpy()
    y = d["y_right"].to_numpy()
    rows = []
    for k in range(n_splits):
        tr, te = folds != k, folds == k
        for block in ("null", "sex", "sex+age"):
            X = _design(d, block)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = sm.Logit(y[tr], X[tr]).fit(disp=0, maxiter=200)
            p = res.predict(X[te])
            rows.append(
                {"fold": k, "block": block, "logloss": _logloss(y[te], p), "auc": _auc(y[te], p)}
            )
    return pd.DataFrame(rows)
