"""On-disk cache for the heavy H2 computations (GLMM fits, bootstraps, cross-validation).

Layout: `data/interim/h2/<step>-<key>.pkl` (outside git). The key is a hash of the step name, its
parameters, a hash of the data and `CODE_VERSION`. Figures read these results and never
recompute them, so changing a plot does not trigger a refit.

The cache does not notice edits to the analysis code. After changing the code of a step, bump
`CODE_VERSION` or delete the matching files (`Cache.clear(step)`).

Only aggregates and row-aligned arrays without user keys are stored.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CODE_VERSION = "2"
DEFAULT_ROOT = Path("data/interim/h2")


def data_hash(df: pd.DataFrame, cols: list[str]) -> str:
    """Short hash of the values of `cols` (row order matters)."""
    h = hashlib.sha256()
    for c in cols:
        h.update(c.encode())
        h.update(pd.util.hash_pandas_object(df[c], index=False).to_numpy().tobytes())
    return h.hexdigest()[:16]


def _default(o: Any) -> Any:
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


class Cache:
    """Pickle cache keyed by (step, params, data hash, code version)."""

    def __init__(self, root: str | Path = DEFAULT_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log: list[dict] = []

    def key(self, step: str, params: dict | None, dhash: str) -> str:
        payload = json.dumps(
            {"step": step, "params": params or {}, "data": dhash, "code": CODE_VERSION},
            sort_keys=True,
            default=_default,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def path(self, step: str, params: dict | None, dhash: str) -> Path:
        return self.root / f"{step}-{self.key(step, params, dhash)}.pkl"

    def get(
        self,
        step: str,
        fn: Callable[[], Any],
        *,
        dhash: str,
        params: dict | None = None,
        force: bool = False,
    ) -> Any:
        """Return the cached result of `fn()`, computing and storing it on a miss."""
        p = self.path(step, params, dhash)
        if p.exists() and not force:
            self.log.append({"step": step, "cached": True, "seconds": 0.0})
            with p.open("rb") as f:
                return pickle.load(f)
        t0 = time.time()
        res = fn()
        sec = time.time() - t0
        with p.open("wb") as f:
            pickle.dump(res, f)
        self.log.append({"step": step, "cached": False, "seconds": sec})
        return res

    def clear(self, step: str | None = None) -> int:
        """Delete cached files of one step (or all); returns the number removed."""
        n = 0
        for p in self.root.glob(f"{step}-*.pkl" if step else "*.pkl"):
            p.unlink()
            n += 1
        return n
