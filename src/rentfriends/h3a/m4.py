"""M4: within-receiver analysis of bio status changes, with a feasibility gate."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rentfriends.h3a import variables as v
from rentfriends.h3a.data import PROFILE_COLS
from rentfriends.h3a.models import fit_fe_logit, sandwich

GATE_MIN_RECEIVERS = 30
MIN_SWIPES_PER_SIDE = 5
OTHER_FIELDS = [c for c in PROFILE_COLS if c not in ("bio", "bio_length")]


def bio_history(history: pd.DataFrame) -> pd.DataFrame:
    """Per version: bio emptiness, text change and status change vs the previous version.

    Changes are detected by comparing snapshots, not `changed_fields` (G17).
    """
    h = history.sort_values(["user_key", "version"]).reset_index(drop=True)
    text = h["bio"].fillna("").astype(str)
    empty = v.bio_empty(h["bio"])
    first = h["user_key"].ne(h["user_key"].shift())
    prev_text = text.shift()
    prev_empty = empty.shift()
    out = pd.DataFrame(
        {
            "user_key": h["user_key"],
            "version": h["version"],
            "day": h["day"],
            "bio_empty": empty,
            "text_change": (~first) & (text != prev_text),
            "status_change": (~first) & (empty != prev_empty),
        }
    )
    other = h[OTHER_FIELDS].astype("string").fillna("<NA>")
    other_changed = (other != other.shift()).any(axis=1) & ~first
    out["other_fields_changed"] = other_changed
    return out


def funnel_and_sample(
    t: pd.DataFrame, history: pd.DataFrame, clean_only: bool = False
) -> tuple[dict, pd.DataFrame]:
    """Feasibility funnel (F6) and the eligible swipe sample.

    Exclusions: swipes assigned to the receiver's `first_version` (status uncertain) and
    swipes on the day of any bio status change of that receiver.
    `clean_only=True` keeps only receivers whose status changes came with no change in any
    other profile field.
    """
    bh = bio_history(history)
    receivers = set(t["r_key"].unique())
    bh = bh[bh["user_key"].isin(receivers)]
    with_text = set(bh.loc[bh["text_change"], "user_key"])
    sc = bh[bh["status_change"]]
    with_status = set(sc["user_key"])
    if clean_only:
        dirty = set(sc.loc[sc["other_fields_changed"], "user_key"])
        with_status = with_status - dirty
    change_days = set(zip(sc["user_key"], sc["day"], strict=True))

    s = t[t["r_key"].isin(with_status)].copy()
    n_before = len(s)
    s = s[s["r_asof_source"] != "first_version"]
    on_change_day = np.array(
        [(k, d) in change_days for k, d in zip(s["r_key"], s["day"], strict=True)], dtype=bool
    )
    s = s[~on_change_day]
    n_after_excl = len(s)
    per = s.groupby(["r_key", "has_bio"]).size().unstack(fill_value=0)
    for c in (0, 1):
        if c not in per.columns:
            per[c] = 0
    ok = per[(per[0] >= MIN_SWIPES_PER_SIDE) & (per[1] >= MIN_SWIPES_PER_SIDE)].index
    s = s[s["r_key"].isin(set(ok))]
    funnel = {
        "receivers_in_sample": len(receivers),
        "with_bio_text_change": len(with_text),
        "with_status_change": len(with_status),
        "swipes_on_status_changers": n_before,
        "swipes_after_exclusions": int(n_after_excl),
        "swipes_eligible_receivers": int(len(s)),
        "with_min_swipes_each_side": len(ok),
        "gate_threshold": GATE_MIN_RECEIVERS,
        "gate_passed": bool(len(ok) >= GATE_MIN_RECEIVERS),
        "clean_only": clean_only,
    }
    return funnel, s


def estimate_lpm(s: pd.DataFrame) -> dict:
    """LPM y ~ has_bio + receiver FE + week FE, SEs clustered by receiver (p.p.)."""
    r = pd.factorize(s["r_key"])[0]
    wk = pd.get_dummies(s["week"], prefix="w", drop_first=True, dtype=float).to_numpy()
    R = np.eye(r.max() + 1)[r]
    X = np.column_stack([s["has_bio"].to_numpy(float), wk, R])
    y = s["y_right"].to_numpy(float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    U = X * (y - X @ beta)[:, None]
    V = sandwich(XtX_inv, U, r, X.shape[1])
    b, se = float(beta[0]), float(np.sqrt(V[0, 0]))
    return {
        "status": "ok",
        "beta_pp": 100 * b,
        "se_pp": 100 * se,
        "lo95_pp": 100 * (b - 1.959964 * se),
        "hi95_pp": 100 * (b + 1.959964 * se),
        "n_obs": int(len(y)),
        "n_receivers": int(r.max() + 1),
    }


def estimate_fe_logit(s: pd.DataFrame) -> dict:
    """Companion FE-logit: receiver FE (profiled), week dummies, SEs clustered by receiver."""
    wk = pd.get_dummies(s["week"], prefix="w", drop_first=True, dtype=float)
    X = np.column_stack([s["has_bio"].to_numpy(float), wk.to_numpy()])
    names = ["has_bio", *wk.columns]
    rk = pd.factorize(s["r_key"])[0]
    return fit_fe_logit(X, s["y_right"].to_numpy(float), rk, rk, names)
