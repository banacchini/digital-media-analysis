"""Small-cell suppression for every table that leaves the analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rentfriends.h3a.config import MIN_CELL_USERS


def suppress_small(
    df: pd.DataFrame,
    n_users_col: str,
    value_cols: list[str] | None = None,
    min_users: int = MIN_CELL_USERS,
) -> pd.DataFrame:
    """Set value columns to NaN where fewer than `min_users` distinct users are behind a cell.

    Adds a boolean `suppressed` column. The user-count column itself is also blanked for
    suppressed cells, so the exact small count is not published.
    """
    out = df.copy()
    small = out[n_users_col] < min_users
    cols = value_cols if value_cols is not None else [c for c in out.columns if c != n_users_col]
    for c in [*cols, n_users_col]:
        if c in out.columns and pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype(float)
            out.loc[small, c] = np.nan
    out["suppressed"] = small.to_numpy()
    return out
