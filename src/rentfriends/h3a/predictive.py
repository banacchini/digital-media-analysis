"""M6: descriptive predictive increment of has_bio (GroupKFold by sender, sender bootstrap)."""

from __future__ import annotations

import numpy as np
from scipy.special import expit
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from rentfriends.h3a.models import _logit_newton


def oof_predictions(
    X: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int, seed: int
) -> np.ndarray:
    """Out-of-fold probabilities from an unpenalised pooled logit, folds by sender."""
    gkf = GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    p = np.empty(len(y))
    for tr, te in gkf.split(X, y, groups):
        Xtr = X[tr]
        keep = Xtr.std(axis=0) > 0
        keep[0] = True  # intercept
        beta, _, _ = _logit_newton(Xtr[:, keep], y[tr])
        p[te] = expit(X[te][:, keep] @ beta)
    return p


def _aucpr(y, p, w=None) -> float:
    """Average precision (area under the precision-recall curve), optionally weighted."""
    return float(average_precision_score(y, p, sample_weight=w))


def _metrics(y, p_base, p_full, w=None):
    eps = 1e-12
    ll = lambda p: -np.average(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps), weights=w)  # noqa: E731
    return (
        ll(p_full) - ll(p_base),
        roc_auc_score(y, p_full, sample_weight=w) - roc_auc_score(y, p_base, sample_weight=w),
        ll(p_base),
        ll(p_full),
        roc_auc_score(y, p_base, sample_weight=w),
        roc_auc_score(y, p_full, sample_weight=w),
        _aucpr(y, p_full, w) - _aucpr(y, p_base, w),
        _aucpr(y, p_base, w),
        _aucpr(y, p_full, w),
    )


def predictive_increment(
    X_base: np.ndarray,
    X_full: np.ndarray,
    y: np.ndarray,
    sender: np.ndarray,
    n_splits: int = 5,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict:
    """Delta log loss (full - base; negative = better) and delta AUC with sender-bootstrap CIs."""
    p_b = oof_predictions(X_base, y, sender, n_splits, seed)
    p_f = oof_predictions(X_full, y, sender, n_splits, seed)
    d_ll, d_auc, ll_b, ll_f, auc_b, auc_f, d_pr, pr_b, pr_f = _metrics(y, p_b, p_f)
    rng = np.random.default_rng(seed)
    G = sender.max() + 1
    boots = np.empty((n_boot, 3))
    for b in range(n_boot):
        draw = rng.integers(0, G, G)
        w = np.bincount(draw, minlength=G)[sender].astype(float)
        m = _metrics(y, p_b, p_f, w)
        boots[b] = (m[0], m[1], m[6])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    return {
        "status": "ok",
        "n_splits": n_splits,
        "n_boot": n_boot,
        "logloss_base": ll_b,
        "logloss_full": ll_f,
        "auc_base": auc_b,
        "auc_full": auc_f,
        "d_logloss": d_ll,
        "d_logloss_lo95": lo[0],
        "d_logloss_hi95": hi[0],
        "d_auc": d_auc,
        "d_auc_lo95": lo[1],
        "d_auc_hi95": hi[1],
        "aucpr_base": pr_b,
        "aucpr_full": pr_f,
        "prevalence": float(np.mean(y)),
        "d_aucpr": d_pr,
        "d_aucpr_lo95": lo[2],
        "d_aucpr_hi95": hi[2],
    }
