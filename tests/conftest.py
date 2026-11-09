"""Shared test fixtures."""

import numpy as np
import pandas as pd


def make_dummy_h1_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    senders = [f"u{i}" for i in rng.integers(1, 20, size=n)]
    receivers = [f"u{i}" for i in rng.integers(21, 50, size=n)]
    return pd.DataFrame(
        {
            "user_key": senders,
            "target_user_key": receivers,
            "y_right": rng.integers(0, 2, size=n),
            "same_band": rng.integers(0, 2, size=n).astype(float),
            "age_band_diff": rng.integers(-2, 3, size=n).astype(float),
            "age_band_diff_abs": rng.integers(0, 3, size=n).astype(float),
            "age_band_sender": rng.choice(["18-20", "21-23", "24-26"], size=n),
            "same_sex": rng.integers(0, 2, size=n).astype(float),
            "sex_pair": rng.choice(["F_F", "F_M", "M_F", "M_M", "F_O"], size=n),
            "interests_jaccard": rng.uniform(0, 1, size=n),
            "interests_shared_n": rng.integers(0, 5, size=n),
            "interests_count_diff_abs": rng.integers(0, 4, size=n),
            "lifestyle_agree_ratio": rng.uniform(0, 1, size=n),
            "lifestyle_tag_conflict": rng.integers(0, 2, size=n),
            "lifestyle_shared_tags_n": rng.integers(0, 3, size=n),
            "city_same": rng.integers(0, 2, size=n).astype(float),
            "city_diff": rng.integers(0, 2, size=n).astype(float),
        }
    )
