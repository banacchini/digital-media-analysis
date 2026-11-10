"""H2 audit follow-up (2026-11): sex decomposition (Z1), age effect (Z2), estimators (Z3), CV (Z4).

All results are aggregates. Heavy steps go through `rentfriends.h2_cache.Cache`, so figures can be
restyled without refitting. Nothing here reads `bio` or exposes `user_key`.

Sex parametrisation (Z1). Let s = +1 for a female sender and -1 for a male sender, rF = 1 when
the receiver is female. The model is

    logit P(right) = a + b s + pi rF + h s rF           (+ crossed random intercepts)

Within a sender sex the F-vs-M receiver log-odds gap is pi + h (female senders) and pi - h (male
senders). Only the two gaps are identified, so the single interaction contrast 2h = gap_F - gap_M
is identified. Reading `h` as an own-sex premium and `pi` as the popularity of female profiles
needs the assumption that popularity and premium are the same for both sender sexes. Sender-
specific premiums are not identified and are not reported.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.metrics import average_precision_score, roc_auc_score

from rentfriends import h2
from rentfriends.h2_cache import Cache, data_hash
from rentfriends.h3a.models import fit_fe_logit, fit_glmm, fit_pooled_logit
from rentfriends.h3a.runner import run_with_timeout

Z95 = float(norm.ppf(0.975))
BANDS4 = ("18-20", "21-23", "24-26", "27+")
BAND4 = {
    "18-20": "18-20",
    "21-23": "21-23",
    "24-26": "24-26",
    "27-30": "27+",
    "31-35": "27+",
    "36+": "27+",
}
MIN_USERS = 5  # cells with fewer distinct senders are suppressed (G12)
GLMM_TIMEOUT_S = 1800.0
HASH_COLS = [
    "sender",
    "receiver",
    "y_right",
    "sender_sex",
    "receiver_sex",
    "sender_band",
    "receiver_band",
    "sender_city",
    "receiver_city",
    "day",
]


# ------------------------------------------------------------------------- data preparation


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add the modelling columns used below (band labels, city dummies, sex coding, int codes)."""
    d = df.copy()
    d["sender_band4"] = d["sender_band"].map(BAND4)
    d["receiver_band4"] = d["receiver_band"].map(BAND4)
    d["diff_abs"] = d["age_band_diff"].abs()
    d["older"] = d["age_band_diff"].clip(lower=0)  # receiver older than sender, in bands
    d["younger"] = (-d["age_band_diff"]).clip(lower=0)
    d["city_same"] = (d["same_city"] == "same").astype(float)
    d["city_diff"] = (d["same_city"] == "different").astype(float)
    d["sender_code"] = pd.factorize(d["sender"], sort=True)[0].astype(np.int64)
    d["receiver_code"] = pd.factorize(d["receiver"], sort=True)[0].astype(np.int64)
    return d


def sex_sample(d: pd.DataFrame) -> pd.DataFrame:
    """Sender and receiver sex F or M only; sex `O` stays outside the main model (G16)."""
    return d[d["sender_sex"].isin(["F", "M"]) & d["receiver_sex"].isin(["F", "M"])].copy()


def age_sample(d: pd.DataFrame) -> pd.DataFrame:
    """Rows with a known age band on both sides (the H2/H3a sample)."""
    return d.dropna(subset=["same_band", "age_band_diff"]).copy()


def sex_pair_dummies(d: pd.DataFrame) -> pd.DataFrame:
    """Ordered sex-pair dummies, reference F>F (as the H1 controls, `F_F` there)."""
    dm = pd.get_dummies(d["sex_pair"], prefix="sex", dtype=float).drop(
        columns=["sex_F>F"], errors="ignore"
    )
    return dm.loc[:, dm.sum() > 0]


# ---------------------------------------------------------------------------- estimators


def _glmm_job(X, y, s, r, names):  # top-level so the spawned child can import it
    return fit_glmm(X, y, s, r, names)


def estimate(
    X: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    receiver: np.ndarray,
    names: list[str],
    *,
    glmm: bool = True,
    timeout_s: float = GLMM_TIMEOUT_S,
) -> dict:
    """Fit pooled logit (two-way clustered) and, if requested, the crossed-RE GLMM (Z3).

    `primary` records which estimator gives the headline number: the GLMM when it converged with
    finite standard errors, otherwise the pooled logit (fallback). Both are always stored.
    """
    pooled = fit_pooled_logit(X, y, sender, receiver, names, bio_col=None)
    out: dict[str, Any] = {"names": list(names), "n": int(len(y)), "pooled": pooled}
    if glmm:
        g = run_with_timeout(_glmm_job, timeout_s, X, y, sender, receiver, names)
        out["glmm"] = g
        ok = (
            g.get("status") == "ok"
            and np.all(np.isfinite(g.get("se", [np.nan])))
            and np.all(np.isfinite(g.get("coef", [np.nan])))
        )
    else:
        ok = False
    out["glmm_ok"] = bool(ok)
    out["primary"] = "GLMM" if ok else "pooled (fallback)"
    return out


def term_table(est: dict, model: str, terms: list[str] | None = None) -> pd.DataFrame:
    """Long table: one row per (estimator, term) with log-odds, SE, OR and Wald 95% CI."""
    rows = []
    for key, label in (("pooled", "pooled (populacyjne)"), ("glmm", "GLMM (warunkowe)")):
        res = est.get(key)
        if not res or "coef" not in res:
            continue
        ok = key == "pooled" or est.get("glmm_ok", False)
        for i, nm in enumerate(res["names"]):
            if nm == "const" or (terms and nm not in terms):
                continue
            b, se = res["coef"][i], res["se"][i]
            b = np.nan if b is None else float(b)
            se = np.nan if se is None or not ok else float(se)
            rows.append(
                {
                    "model": model,
                    "term": nm,
                    "estimator": label,
                    "converged_with_se": bool(ok),
                    "coef": b,
                    "se": se,
                    "or": float(np.exp(b)),
                    "or_lo": float(np.exp(b - Z95 * se)),
                    "or_hi": float(np.exp(b + Z95 * se)),
                }
            )
    return pd.DataFrame(rows)


def linear_combo(res: dict, weights: dict[str, float]) -> tuple[float, float]:
    """Estimate and SE of sum_j w_j beta_j from a pooled fit (uses its covariance)."""
    idx = {n: i for i, n in enumerate(res["names"])}
    w = np.zeros(len(idx))
    for k, v in weights.items():
        w[idx[k]] = v
    b = float(w @ np.asarray(res["coef"]))
    V = np.asarray(res["cov"])
    return b, float(np.sqrt(w @ V @ w))


# --------------------------------------------------------------------------- Z1: sex


Z1_CONTROLS = ["age_band_diff", "diff_abs", "same_band", "city_same", "city_diff"]
Z1_CODINGS = ("pm", "refF", "refM")


def z1_design(d: pd.DataFrame, coding: str, controls: bool):
    """Design matrix for the sex decomposition; see the module docstring.

    `pm`: s = +/-1; terms `receiver_F` (pi) and `sender_F:receiver_F` (h).
    `refF`/`refM`: 0/1 sender dummy so that `receiver_F` is the F-vs-M receiver gap of the
    reference sender sex (F senders for `refF`, M senders for `refM`); used for gap CIs.
    """
    if controls:
        d = d.dropna(subset=Z1_CONTROLS)
    sf = (d["sender_sex"] == "F").to_numpy().astype(float)
    rf = (d["receiver_sex"] == "F").to_numpy().astype(float)
    if coding == "pm":
        s, sname = 2 * sf - 1, "sender_F"
    elif coding == "refF":
        s, sname = 1 - sf, "sender_M"
    elif coding == "refM":
        s, sname = sf, "sender_F"
    else:
        raise ValueError(coding)
    cols = [np.ones(len(d)), s, rf, s * rf]
    names = ["const", sname, "receiver_F", f"{sname}:receiver_F"]
    if controls:
        for c in Z1_CONTROLS:
            cols.append(d[c].to_numpy(float))
            names.append(c)
    X = np.column_stack(cols)
    return d, X, d["y_right"].to_numpy(float), names


def z1_fit(d: pd.DataFrame, controls: bool, *, glmm: bool = True) -> dict:
    """Z1 (a): the three codings, pooled and GLMM, plus sample sizes."""
    out: dict[str, Any] = {"controls": controls}
    for coding in Z1_CODINGS:
        dd, X, y, names = z1_design(d, coding, controls)
        out[coding] = estimate(
            X, y, dd["sender_code"].to_numpy(), dd["receiver_code"].to_numpy(), names, glmm=glmm
        )
    out["n"] = int(len(dd))
    out["n_senders"] = int(dd["sender_code"].nunique())
    out["n_receivers"] = int(dd["receiver_code"].nunique())
    return out


def z1_derived(fit: dict) -> pd.DataFrame:
    """Headline quantities of Z1 from a `z1_fit` result, per estimator.

    - `gap_F`, `gap_M`: OR of a female vs male receiver among female / male senders (identified);
    - `or_same_F`, `or_same_M`: OR same-vs-different sex per sender sex (= gap_F, 1/gap_M);
    - `h` (own-sex premium) and `pi` (female-profile popularity), identified only under the
      symmetry assumption of the module docstring; `or_h = exp(h)`, `or_pi = exp(pi)`.
    - `ratio_of_gaps = exp(2h)`: assumption-free interaction contrast.
    """
    rows = []
    for key, label in (("pooled", "pooled (populacyjne)"), ("glmm", "GLMM (warunkowe)")):
        if key == "glmm" and not fit["pm"].get("glmm_ok", False):
            continue
        r_pm, r_f, r_m = (fit[c][key] for c in Z1_CODINGS)
        b_pi, se_pi = _coef(r_pm, "receiver_F")
        b_h, se_h = _coef(r_pm, "sender_F:receiver_F")
        b_gf, se_gf = _coef(r_f, "receiver_F")  # refF: F senders
        b_gm, se_gm = _coef(r_m, "receiver_F")  # refM: M senders
        for name, b, se in (
            ("pi: popularność profili F (przy symetrii)", b_pi, se_pi),
            ("h: premia za własną płeć (przy symetrii)", b_h, se_h),
            ("gap_F: odbiorca F vs M, nadawcy F", b_gf, se_gf),
            ("gap_M: odbiorca F vs M, nadawcy M", b_gm, se_gm),
        ):
            rows.append(_row(label, name, b, se))
        # same-vs-different sex OR for male senders is 1 / gap_M
        rows.append(_row(label, "or_same_M: ta sama vs inna płeć, nadawcy M", -b_gm, se_gm))
        rows.append(_row(label, "ratio_of_gaps = 2h (bez założeń)", 2 * b_h, 2 * se_h))
    out = pd.DataFrame(rows)
    out["controls"] = fit["controls"]
    return out


def _coef(res: dict, name: str) -> tuple[float, float]:
    i = res["names"].index(name)
    se = res["se"][i]
    return float(res["coef"][i]), float(np.nan if se is None else se)


def _row(estimator: str, quantity: str, b: float, se: float) -> dict:
    return {
        "estimator": estimator,
        "quantity": quantity,
        "log_or": b,
        "se": se,
        "or": float(np.exp(b)),
        "or_lo": float(np.exp(b - Z95 * se)),
        "or_hi": float(np.exp(b + Z95 * se)),
    }


def z1_fixed_effects(d: pd.DataFrame, controls: bool) -> dict:
    """Z1 (b): sender fixed effects; `receiver_F` as main effect, and with the sender-sex term.

    Compares how the *same sender* treats female and male profiles. `receiver_F` is a property
    of the receiver correlated with other traits (age, city), so it is not a pure popularity
    measure. SEs are clustered on the receiver only (`fit_fe_logit`).
    """
    out = {}
    for variant in ("main_effect", "with_interaction"):
        dd = d.dropna(subset=Z1_CONTROLS) if controls else d
        sf = (dd["sender_sex"] == "F").to_numpy().astype(float)
        rf = (dd["receiver_sex"] == "F").to_numpy().astype(float)
        cols, names = [rf], ["receiver_F"]
        if variant == "with_interaction":
            cols.append((2 * sf - 1) * rf)
            names.append("sender_F:receiver_F")
        if controls:
            cols += [dd[c].to_numpy(float) for c in Z1_CONTROLS]
            names += Z1_CONTROLS
        X = np.column_stack(cols)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out[variant] = fit_fe_logit(
                X,
                dd["y_right"].to_numpy(float),
                dd["sender_code"].to_numpy(),
                dd["receiver_code"].to_numpy(),
                names,
            )
    return out


def z1_lme4(d: pd.DataFrame, controls: bool) -> dict:
    """Cross-check of the main GLMM in R (`glmer`, nAGQ = 0), integer codes only."""
    from rentfriends.h3a.analysis import lme4_fit

    dd, X, y, names = z1_design(d, "pm", controls)
    return lme4_fit(
        X, y, dd["sender_code"].to_numpy(), dd["receiver_code"].to_numpy(), names, GLMM_TIMEOUT_S
    )


# ---------------------------------------------------------------------- Z2: age matrix/model


def age_matrix(
    d: pd.DataFrame, n_boot: int = 1000, seed: int = 0, level: float = 0.95
) -> pd.DataFrame:
    """P(right) by sender band x receiver band with a sender-cluster bootstrap CI.

    Cells with fewer than `MIN_USERS` distinct senders have n, k, rate and CI blanked.
    """
    d = d.dropna(subset=["sender_band4", "receiver_band4"])
    codes = d["sender_code"].to_numpy()
    uniq, inv = np.unique(codes, return_inverse=True)
    n_s = len(uniq)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_s, size=(n_boot, n_s))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    y = d["y_right"].to_numpy()
    rows = []
    for a in BANDS4:
        for b in BANDS4:
            m = ((d["sender_band4"] == a) & (d["receiver_band4"] == b)).to_numpy()
            n_c = np.bincount(inv[m], minlength=n_s).astype(float)
            k_c = np.bincount(inv[m], weights=y[m], minlength=n_s)
            n_users = int((n_c > 0).sum())
            row = {"sender_band": a, "receiver_band": b, "n_senders": n_users}
            if n_users < MIN_USERS:
                row |= dict(n=np.nan, k=np.nan, rate=np.nan, ci_low=np.nan, ci_high=np.nan)
                row["n_senders"] = np.nan
                row["suppressed"] = True
            else:
                with np.errstate(invalid="ignore", divide="ignore"):
                    boot = k_c[idx].sum(1) / n_c[idx].sum(1)
                lo, hi = np.nanquantile(boot, [lo_q, hi_q])
                row |= dict(
                    n=int(n_c.sum()),
                    k=int(k_c.sum()),
                    rate=k_c.sum() / n_c.sum(),
                    ci_low=lo,
                    ci_high=hi,
                    suppressed=False,
                )
            rows.append(row)
    return pd.DataFrame(rows)


def age_design(d: pd.DataFrame, param: str, fe_band: bool, controls: bool = True):
    """Design for the age model; `param` is `linear` (diff_abs, diff) or `dir` (older, younger).

    `linear` is the H1 age block (`same_band`, `age_band_diff_abs`, `age_band_diff`); `dir`
    spans the same model but gives the per-band log-odds of an older / younger receiver directly.
    Controls (identical to H1): ordered sex pair (ref F>F) and city same/different.
    """
    need = ["same_band", "age_band_diff", "sex_pair"]
    d = d.dropna(subset=need)
    cols = {"const": np.ones(len(d)), "same_band": d["same_band"].to_numpy(float)}
    if param == "linear":
        cols["age_band_diff_abs"] = d["diff_abs"].to_numpy(float)
        cols["age_band_diff"] = d["age_band_diff"].to_numpy(float)
    elif param == "dir":
        cols["older_per_band"] = d["older"].to_numpy(float)
        cols["younger_per_band"] = d["younger"].to_numpy(float)
    else:
        raise ValueError(param)
    if controls:
        for c in sex_pair_dummies(d).columns:
            cols[c] = sex_pair_dummies(d)[c].to_numpy()
        cols["city_same"] = d["city_same"].to_numpy(float)
        cols["city_diff"] = d["city_diff"].to_numpy(float)
    if fe_band:
        sb = pd.get_dummies(d["sender_band4"], prefix="sband", dtype=float)
        for c in sb.columns:
            if c != "sband_18-20":
                cols[c] = sb[c].to_numpy()
    # drop constant columns (e.g. a city level absent from the sample); `const` stays
    cols = {k: v for k, v in cols.items() if k == "const" or np.ptp(v) > 0}
    names = list(cols)
    return d, np.column_stack(list(cols.values())), d["y_right"].to_numpy(float), names


def z2_models(d: pd.DataFrame, *, glmm: bool = True) -> dict:
    """Z2 (b, c): `same_band`, `age_band_diff_abs`, `age_band_diff` with and without band FE."""
    out = {}
    for fe in (False, True):
        for param in ("linear", "dir"):
            dd, X, y, names = age_design(d, param, fe)
            out[f"{param}|fe={int(fe)}"] = estimate(
                X, y, dd["sender_code"].to_numpy(), dd["receiver_code"].to_numpy(), names, glmm=glmm
            )
    out["n"] = int(len(dd))
    return out


def age_dummy_design(d: pd.DataFrame, controls: bool):
    """Dummies of the H1 age-direction check: younger 2+/1, older 1/2+, sender-band FE."""
    diff = d["age_band_diff"]
    cols = {
        "const": np.ones(len(d)),
        "younger_by_2plus": (diff <= -2).to_numpy(float),
        "younger_by_1": (diff == -1).to_numpy(float),
        "older_by_1": (diff == 1).to_numpy(float),
        "older_by_2plus": (diff >= 2).to_numpy(float),
    }
    sb = pd.get_dummies(d["sender_band4"], prefix="sband", dtype=float)
    for c in sb.columns:
        if c != "sband_18-20":
            cols[c] = sb[c].to_numpy()
    if controls:
        sp = sex_pair_dummies(d)
        for c in sp.columns:
            cols[c] = sp[c].to_numpy()
        cols["city_same"] = d["city_same"].to_numpy(float)
        cols["city_diff"] = d["city_diff"].to_numpy(float)
    return np.column_stack(list(cols.values())), list(cols)


def h1_bridge(d_h2: pd.DataFrame, h1_df: pd.DataFrame) -> pd.DataFrame:
    """Z2: why age ORs differ from H1. Same dummy spec, changing one thing at a time.

    Steps (all with sender-band FE and the H1 dummies):
    1. H1 sample (92 754), `age_direction_check`, SE clustered on sender (H1's published numbers);
    2. H2 sample (93 717), same function: effect of the sample;
    3. H2 sample, two-way clustering (sender, receiver): effect of the clustering;
    4. + ordered sex pair and city controls: effect of the controls.
    """
    from rentfriends.h1_audit import age_direction_check

    rows = []

    def add(step: str, n: int, pooled: pd.DataFrame):
        for _, r in pooled.iterrows():
            rows.append(
                {
                    "step": step,
                    "n": n,
                    "term": r["term"],
                    "or": r["or"],
                    "or_lo": r["ci_low"],
                    "or_hi": r["ci_high"],
                }
            )

    h1s = h1_df[(h1_df["lifestyle_known_count"] > 0)].dropna(subset=["age_band_diff"])
    chk = age_direction_check(h1s, n_boot=10)["pooled"]
    add("1. próba H1 (92 754), SE po nadawcy", len(h1s), chk)

    d2 = d_h2.assign(age_band_sender=d_h2["sender_band4"], user_key=d_h2["sender"])
    add(
        "2. próba H2 (93 717), SE po nadawcy", len(d2), age_direction_check(d2, n_boot=10)["pooled"]
    )

    for step, ctrl in (
        ("3. + klastry nadawca i odbiorca", False),
        ("4. + kontrole: para płci, miasto", True),
    ):
        dd = d_h2.dropna(subset=["sex_pair"]) if ctrl else d_h2
        X, names = age_dummy_design(dd, ctrl)
        res = fit_pooled_logit(
            X,
            dd["y_right"].to_numpy(float),
            dd["sender_code"].to_numpy(),
            dd["receiver_code"].to_numpy(),
            names,
            bio_col=None,
        )
        t = term_table({"pooled": res}, step)
        t = t[t["term"].str.contains("_by_")]
        add(
            step,
            len(dd),
            t.rename(columns={"or_lo": "ci_low", "or_hi": "ci_high"})[
                ["term", "or", "ci_low", "ci_high"]
            ],
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------ Z4: validation

CV_BLOCKS = ("null", "sex", "sex+age", "sex+age3")
CV_PAIRS = (("sex", "null"), ("sex+age", "sex"), ("sex+age3", "sex"), ("sex+age3", "null"))
CV_METRICS = ("logloss", "auc", "auc_pr")


def cv_design(d: pd.DataFrame, block: str) -> np.ndarray:
    """`sex+age` is the pre-audit block (diff, same band); `sex+age3` adds `age_band_diff_abs`."""
    if block != "sex+age3":
        return h2._design(d, block)
    base = h2._design(d, "sex+age")
    return np.column_stack([base, d["diff_abs"].to_numpy(float)])


def cv_oof(d: pd.DataFrame, group: str, n_splits: int = 5, seed: int = 0) -> dict:
    """Out-of-fold predictions of every block; folds grouped by `sender` or `receiver`."""
    d = d.dropna(subset=["sex_pair", "age_band_diff", "same_band"]).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    keys = d[group].unique()
    fold_of = dict(zip(keys, rng.permutation(len(keys)) % n_splits, strict=True))
    folds = d[group].map(fold_of).to_numpy()
    y = d["y_right"].to_numpy(float)
    pred = {b: np.empty(len(d)) for b in CV_BLOCKS}
    for b in CV_BLOCKS:
        X = cv_design(d, b)
        X = X[:, np.r_[True, X[:, 1:].std(0) > 0]]  # drop all-constant columns (absent pairs)
        for k in range(n_splits):
            tr, te = folds != k, folds == k
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = sm.Logit(y[tr], X[tr]).fit(disp=0, maxiter=200)
            pred[b][te] = res.predict(X[te])
    # Pooling out-of-fold predictions mixes fold-specific intercepts. For the intercept-only
    # model that creates a spurious AUC != 0.5 (and inflates every AUC difference against it),
    # so the null model predicts one constant: AUC = 0.5 and AUC-PR = prevalence by construction.
    # Its log loss changes by < 1e-4 relative to fold-specific constants.
    pred["null"][:] = y.mean()
    return {
        "group": group,
        "y": y,
        "sender_code": d["sender_code"].to_numpy(),
        "folds": folds,
        "pred": pred,
        "n": len(d),
    }


def _metrics(y: np.ndarray, p: np.ndarray, w: np.ndarray | None = None) -> dict[str, float]:
    if w is not None:
        keep = w > 0
        y, p, w = y[keep], p[keep], w[keep]
    pc = np.clip(p, 1e-9, 1 - 1e-9)
    ll = -(y * np.log(pc) + (1 - y) * np.log(1 - pc))
    return {
        "logloss": float(np.average(ll, weights=w)),
        "auc": float(roc_auc_score(y, p, sample_weight=w)),
        "auc_pr": float(average_precision_score(y, p, sample_weight=w)),
    }


def _boot_chunk(y, pred, scode, counts):
    out = []
    for c in counts:
        w = c[scode].astype(float)
        out.append({b: _metrics(y, p, w) for b, p in pred.items()})
    return out


def cv_summary(oof: dict, n_boot: int = 1000, seed: int = 0, level: float = 0.95) -> dict:
    """Pooled OOF metrics, per-fold values and paired differences with sender-bootstrap CIs.

    The bootstrap resamples whole senders and recomputes every metric on the stored out-of-fold
    predictions (no refit), so a difference of two blocks is evaluated on the same resample.
    """
    y, pred, folds = oof["y"], oof["pred"], oof["folds"]
    scode = pd.factorize(oof["sender_code"])[0]
    n_s = int(scode.max()) + 1
    rng = np.random.default_rng(seed)
    counts = np.stack(
        [np.bincount(rng.integers(0, n_s, n_s), minlength=n_s) for _ in range(n_boot)]
    )
    chunks = np.array_split(counts, 16)
    parts = Parallel(n_jobs=-1)(delayed(_boot_chunk)(y, pred, scode, c) for c in chunks)
    boot = [r for part in parts for r in part]

    point = {b: _metrics(y, pred[b]) for b in pred}
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for b in pred:
        for m in CV_METRICS:
            v = np.array([r[b][m] for r in boot])
            rows.append(
                {
                    "block": b,
                    "metric": m,
                    "value": point[b][m],
                    "ci_low": np.quantile(v, lo_q),
                    "ci_high": np.quantile(v, hi_q),
                }
            )
    drows = []
    for big, small in CV_PAIRS:
        for m in CV_METRICS:
            v = np.array([r[big][m] - r[small][m] for r in boot])
            drows.append(
                {
                    "comparison": f"{big} vs {small}",
                    "metric": m,
                    "delta": point[big][m] - point[small][m],
                    "ci_low": np.quantile(v, lo_q),
                    "ci_high": np.quantile(v, hi_q),
                }
            )
    frows = []
    for k in np.unique(folds):
        te = folds == k
        for b in pred:
            frows.append({"fold": int(k), "block": b, **_metrics(y[te], pred[b][te])})
    return {
        "group": oof["group"],
        "n": oof["n"],
        "metrics": pd.DataFrame(rows),
        "deltas": pd.DataFrame(drows),
        "per_fold": pd.DataFrame(frows),
        "n_boot": n_boot,
    }


# --------------------------------------------------------------------------- orchestration


def sensitivity(tables: h2.Tables, df: pd.DataFrame) -> pd.DataFrame:
    """The six pre-registered sensitivity scenarios of the notebook (crude OR by sender sex)."""
    scenarios = {
        "main (as-of, no Hyderabad)": df,
        "current profile (users table)": h2.build_swipe_table(tables, feature_version="users"),
        "only prior_version swipes": df[df["asof_source"] == "prior_version"],
        "with Hyderabad": h2.build_swipe_table(tables, drop_hyderabad=False),
        "without extreme senders (G10)": df[~df["sender_extreme"]],
        f"senders with >= {h2.MIN_SWIPES_ACTIVE} swipes": df[
            df["sender_n"] >= h2.MIN_SWIPES_ACTIVE
        ],
    }
    out = []
    for name, d in scenarios.items():
        r = h2.or_by_sender_sex(d)
        r.insert(0, "scenario", name)
        r.insert(1, "scenario_swipes", len(d))
        out.append(r)
    return pd.concat(out, ignore_index=True)


def run_all(
    df: pd.DataFrame,
    h1_df: pd.DataFrame | None,
    cache: Cache | None = None,
    *,
    tables: h2.Tables | None = None,
    n_boot: int = 1000,
    seed: int = 20261102,
    glmm: bool = True,
    force: bool = False,
    log: Callable[[str], None] | None = print,
) -> dict[str, Any]:
    """Compute (or load from cache) every table behind Z1-Z4. Figures only read this dict."""
    cache = cache or Cache()
    dp = prepare(df)
    dh = data_hash(df, HASH_COLS)
    ds, da = sex_sample(dp), age_sample(dp)
    R: dict[str, Any] = {"data_hash": dh}

    def step(name: str, fn: Callable[[], Any], **params):
        res = cache.get(name, fn, dhash=dh, params=params, force=force)
        if log:
            e = cache.log[-1]
            log(f"{name}: " + ("cache" if e["cached"] else f"{e['seconds']:.0f} s"))
        return res

    R["sizes"] = {
        "rows": len(dp),
        "z1_bare": len(ds),
        "z1_controls": len(ds.dropna(subset=Z1_CONTROLS)),
        "age": len(da),
    }
    # pre-audit analyses of the notebook (kept so the whole notebook reads from the cache)
    R["or_crude"] = step("or_crude", lambda: h2.or_by_sender_sex(df))
    R["or_adjusted"] = step("or_adjusted", lambda: h2.or_by_sender_sex(df, controls=True))
    R["perm"] = step(
        "perm",
        lambda: {g: h2.permutation_null_or(df, g, n_perm=n_boot, seed=seed) for g in ("F", "M")},
        n_perm=n_boot,
    )
    if tables is not None:
        R["sensitivity"] = step("sensitivity", lambda: sensitivity(tables, df))
    R["old_cv"] = step("old_cv", lambda: h2.grouped_cv(df, n_splits=5, seed=seed))
    R["z1_matrix"] = step(
        "z1_matrix", lambda: h2.rate_matrix(dp, n_boot=n_boot, seed=seed), n_boot=n_boot
    )
    for tag, ctrl in (("bare", False), ("controls", True)):
        R[f"z1_fit_{tag}"] = step(
            f"z1_fit_{tag}", lambda c=ctrl: z1_fit(ds, c, glmm=glmm), glmm=glmm
        )
        R[f"z1_derived_{tag}"] = z1_derived(R[f"z1_fit_{tag}"])
        R[f"z1_fe_{tag}"] = step(f"z1_fe_{tag}", lambda c=ctrl: z1_fixed_effects(ds, c))
    R["z1_lme4_bare"] = step("z1_lme4_bare", lambda: z1_lme4(ds, False)) if glmm else None
    R["z2_matrix"] = step("z2_matrix", lambda: age_matrix(da, n_boot, seed), n_boot=n_boot)
    R["z2_models"] = step("z2_models", lambda: z2_models(da, glmm=glmm), glmm=glmm)
    if h1_df is not None:
        R["z2_bridge"] = step("z2_bridge", lambda: h1_bridge(da, h1_df))
    for group in ("sender", "receiver"):
        oof = step(f"z4_oof_{group}", lambda g=group: cv_oof(dp, g, 5, seed))
        R[f"z4_cv_{group}"] = step(
            f"z4_cv_{group}", lambda o=oof: cv_summary(o, n_boot, seed), n_boot=n_boot
        )
    return R


def main() -> None:  # pragma: no cover - convenience entry point
    """Precompute every cached step: `uv run --frozen python -m rentfriends.h2_audit`."""
    from pathlib import Path

    tables = h2.load_tables(Path("data/processed"))
    df = h2.build_swipe_table(tables)
    h1_path = Path("data/processed/h1_analysis_dataset_v1.parquet")
    h1_df = pd.read_parquet(h1_path) if h1_path.exists() else None
    run_all(df, h1_df, tables=tables)


if __name__ == "__main__":  # pragma: no cover
    main()
