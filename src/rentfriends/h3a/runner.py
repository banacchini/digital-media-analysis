"""Timeouts, on-disk cache of aggregated model results, and the step timing log."""

from __future__ import annotations

import csv
import hashlib
import json
import multiprocessing as mp
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


def _child(q, fn, args, kwargs):  # pragma: no cover - runs in a subprocess
    try:
        q.put(("ok", fn(*args, **kwargs)))
    except Exception as e:  # noqa: BLE001
        q.put(("error", repr(e)))


def run_with_timeout(fn, timeout_s: float, *args, **kwargs) -> dict:
    """Run `fn` in a spawned subprocess; return {'status': 'timeout'} after `timeout_s`.

    `spawn` (not fork) keeps OpenMP/BLAS state of the parent out of the child.
    """
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_child, args=(q, fn, args, kwargs), daemon=True)
    t0 = time.time()
    p.start()
    try:
        kind, payload = q.get(timeout=timeout_s)
    except Exception:  # queue.Empty
        p.terminate()
        p.join(5)
        return {"status": "timeout", "time_s": time.time() - t0}
    p.join(30)
    if kind == "error":
        return {"status": "failed", "error": payload, "time_s": time.time() - t0}
    return payload


def _jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, float) and (o != o):
        return None
    return o


def fingerprint(*arrays: np.ndarray, extra: Any = None) -> str:
    """Short hash of model inputs, so a cached result is reused only for identical data."""
    h = hashlib.sha256()
    for a in arrays:
        a = np.ascontiguousarray(a)
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    h.update(json.dumps(_jsonable(extra), sort_keys=True).encode())
    return h.hexdigest()[:16]


class Runner:
    """Holds the report directory, cache and timing log for one notebook run."""

    def __init__(self, report_dir: str | Path, timeout_min: float = 90.0):
        self.dir = Path(report_dir)
        self.cache_dir = self.dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_s = timeout_min * 60
        self.timings = self.dir / "timings.csv"
        if not self.timings.exists():
            with self.timings.open("w", newline="") as f:
                csv.writer(f).writerow(["timestamp", "step", "seconds", "status", "cached"])

    def log_time(self, step: str, seconds: float, status: str = "ok", cached: bool = False):
        with self.timings.open("a", newline="") as f:
            csv.writer(f).writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    step,
                    f"{seconds:.2f}",
                    status,
                    cached,
                ]
            )

    @contextmanager
    def step(self, name: str):
        t0 = time.time()
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            self.log_time(name, time.time() - t0, status)

    def fit(self, key: str, fn, *args, fp: str, timeout: bool = True, **kwargs) -> dict:
        """Cached, timed, optionally time-limited model fit. Results are aggregates only."""
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            cached = json.loads(path.read_text())
            if cached.get("_fingerprint") == fp:
                self.log_time(f"fit:{key}", 0.0, cached.get("status", "?"), cached=True)
                return cached
        t0 = time.time()
        if timeout:
            res = run_with_timeout(fn, self.timeout_s, *args, **kwargs)
        else:
            try:
                res = fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                res = {"status": "failed", "error": repr(e)}
        res = _jsonable(res)
        res["_fingerprint"] = fp
        res["_wall_s"] = time.time() - t0
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        self.log_time(f"fit:{key}", res["_wall_s"], res.get("status", "?"))
        return res

    def save_json(self, name: str, obj: Any) -> None:
        (self.dir / name).write_text(json.dumps(_jsonable(obj), ensure_ascii=False, indent=1))
