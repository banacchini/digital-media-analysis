"""Synthetic RentFriends-shaped tables for testing analysis code before real data arrives.

The tables mimic the schema in `docs/data-statement.md` (`users`, `swipes`, `profile_history`)
and nothing else: no real rows, no bios. The generating process has a known sender-sex effect
(`true_log_or`), sender "generosity" and receiver "popularity" random effects, a few sex changes
over time and a couple of extreme (bot-like) senders, so estimators can be checked against truth.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rentfriends.h2 import AGE_BANDS, Tables

# Log odds ratio of a right swipe for same vs different sex, by sender sex.
DEFAULT_TRUE_LOG_OR = {"F": 1.0, "M": 0.4, "O": 0.0}


def make_synthetic_tables(
    n_users: int = 800,
    swipes_per_user: int = 40,
    true_log_or: dict[str, float] | None = None,
    generosity_sd: float = 0.8,
    popularity_sd: float = 0.6,
    seed: int = 0,
) -> tuple[Tables, dict[str, float]]:
    """Return synthetic (users, swipes, profile_history) and the true log OR per sender sex.

    The true log OR is conditional on the sender and receiver effects. With non-zero
    `generosity_sd` / `popularity_sd` the population-averaged OR that a plain logit estimates is
    smaller (attenuated); with both at 0 the two coincide.
    """
    truth = dict(DEFAULT_TRUE_LOG_OR if true_log_or is None else true_log_or)
    rng = np.random.default_rng(seed)

    keys = np.array([f"u{i:05d}" for i in range(n_users)])
    sex = rng.choice(["F", "M", "O"], size=n_users, p=[0.5, 0.45, 0.05])
    band = rng.choice(AGE_BANDS, size=n_users, p=[0.54, 0.2, 0.1, 0.08, 0.05, 0.03])
    city = rng.choice(
        ["Wrocław", "inne", "Warszawa", "Hyderabad"], size=n_users, p=[0.4, 0.3, 0.27, 0.03]
    )
    users = pd.DataFrame({"user_key": keys, "sex": sex, "age_band": band, "city": city})
    users.loc[rng.random(n_users) < 0.01, "age_band"] = None  # a few missing bands

    # profile history: v1 at a random day, a few users change sex later (as in G16)
    first_day = rng.integers(1, 60, size=n_users)
    hist_rows = []
    old_sex = users["sex"].copy()
    changers = rng.random(n_users) < 0.04
    for i in range(n_users):
        if i % 50 == 0:
            continue  # users without history
        hist_rows.append(
            (
                keys[i],
                1,
                int(first_day[i]),
                "create",
                users.at[i, "sex"],
                users.at[i, "age_band"],
                users.at[i, "city"],
            )
        )
        if changers[i]:
            # the current sex is the changed one; v1 holds a different value
            other = [s for s in ("F", "M") if s != users.at[i, "sex"]][0]
            old_sex.iloc[i] = other
            hist_rows[-1] = (
                keys[i],
                1,
                int(first_day[i]),
                "create",
                other,
                users.at[i, "age_band"],
                users.at[i, "city"],
            )
            hist_rows.append(
                (
                    keys[i],
                    2,
                    int(first_day[i]) + int(rng.integers(5, 40)),
                    "update",
                    users.at[i, "sex"],
                    users.at[i, "age_band"],
                    users.at[i, "city"],
                )
            )
    history = pd.DataFrame(
        hist_rows, columns=["user_key", "version", "day", "change_type", "sex", "age_band", "city"]
    )

    # swipes with generosity and popularity random effects
    generosity = rng.normal(-1.2, generosity_sd, n_users)
    popularity = rng.normal(0.0, popularity_sd, n_users)
    rows = []
    for i in range(n_users):
        targets = rng.choice(np.delete(np.arange(n_users), i), size=swipes_per_user, replace=False)
        same = (sex[targets] == sex[i]).astype(float)
        eta = generosity[i] + popularity[targets] + truth.get(sex[i], 0.0) * same
        p = 1 / (1 + np.exp(-eta))
        right = rng.random(swipes_per_user) < p
        days = rng.integers(1, 113, size=swipes_per_user)
        for t, r, dday in zip(targets, right, days, strict=True):
            rows.append((keys[i], "profile", keys[t], "right" if r else "left", int(dday)))
    swipes = pd.DataFrame(
        rows, columns=["user_key", "target_type", "target_user_key", "direction", "day"]
    )

    # extreme senders (bots): all right / all left
    bots = rng.choice(n_users, size=6, replace=False)
    swipes.loc[swipes["user_key"].isin(keys[bots[:3]]), "direction"] = "right"
    swipes.loc[swipes["user_key"].isin(keys[bots[3:]]), "direction"] = "left"

    # listing swipes and one self-swipe that the analysis must drop
    listing = pd.DataFrame(
        {
            "user_key": keys[:30],
            "target_type": "listing",
            "target_user_key": None,
            "direction": "right",
            "day": 10,
        }
    )
    selfswipe = pd.DataFrame([(keys[1], "profile", keys[1], "right", 5)], columns=swipes.columns)
    swipes = pd.concat([swipes, listing, selfswipe], ignore_index=True)
    return Tables(users=users, swipes=swipes, profile_history=history), truth
