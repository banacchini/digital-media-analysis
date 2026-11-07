"""GLMM sanity check: simulate y on the real design with known parameters and refit."""

from __future__ import annotations

import numpy as np
from scipy.special import expit

from rentfriends.h3a.classify import Z95
from rentfriends.h3a.models import fit_glmm

TRUE_VAR_SENDER = 1.5
TRUE_VAR_RECEIVER = 0.5
TRUE_BETA_BIO = 0.15
TRUE_INTERCEPT = -1.8


def simulate_y(X, names, sender, receiver, seed):
    """Bernoulli outcome with crossed random intercepts; only const and has_bio are non-zero."""
    rng = np.random.default_rng(seed)
    beta = np.zeros(X.shape[1])
    beta[names.index("const")] = TRUE_INTERCEPT
    beta[names.index("has_bio")] = TRUE_BETA_BIO
    us = rng.normal(0, np.sqrt(TRUE_VAR_SENDER), sender.max() + 1)
    ur = rng.normal(0, np.sqrt(TRUE_VAR_RECEIVER), receiver.max() + 1)
    eta = X @ beta + us[sender] + ur[receiver]
    return rng.binomial(1, expit(eta)).astype(float)


def sim_rep(X, names, sender, receiver, seed) -> dict:
    """One replication (runs in a subprocess via Runner.fit)."""
    y = simulate_y(X, names, sender, receiver, seed)
    res = fit_glmm(X, y, sender, receiver, names)
    return res


def summarise(reps: list[dict]) -> dict:
    """Bias, empirical SD vs mean SE, and 95% coverage for has_bio and the variances."""
    ok = [r for r in reps if r.get("status") == "ok"]
    out = {"n_reps": len(reps), "n_ok": len(ok)}
    if not ok:
        return out
    j = ok[0]["names"].index("has_bio")
    b = np.array([r["coef"][j] for r in ok])
    se = np.array([r["se"][j] for r in ok])
    cover = np.mean((b - Z95 * se <= TRUE_BETA_BIO) & (b + Z95 * se >= TRUE_BETA_BIO))
    vs = np.array([r["var_sender"] for r in ok])
    vr = np.array([r["var_receiver"] for r in ok])
    out.update(
        {
            "true_beta_bio": TRUE_BETA_BIO,
            "mean_beta_bio": float(b.mean()),
            "bias_beta_bio": float(b.mean() - TRUE_BETA_BIO),
            "emp_sd_beta_bio": float(b.std(ddof=1)) if len(b) > 1 else float("nan"),
            "mean_se_beta_bio": float(se.mean()),
            "coverage95_beta_bio": float(cover),
            "true_var_sender": TRUE_VAR_SENDER,
            "mean_var_sender": float(vs.mean()),
            "true_var_receiver": TRUE_VAR_RECEIVER,
            "mean_var_receiver": float(vr.mean()),
            "mean_fit_s": float(np.mean([r["time_s"] for r in ok])),
            "optimizers": sorted({r["optimizer"] for r in ok}),
        }
    )
    return out
