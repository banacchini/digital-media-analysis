"""Prevalence diagnostics for the D15 lifestyle tag conflict (`lifestyle_tag_conflict`).

Works on the lifestyle tag sets of the two sides of every swipe (canonical tags, never bio text)
and returns aggregates only. The independence baseline reassigns the receivers' tag sets between
swipes: it keeps both marginal tag distributions and destroys the sender-receiver link, so it
shows how many conflicts exist by chance alone.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from rentfriends import dataset_h1 as d1
from rentfriends import h1_tagval as tv

PolarityPairs = list[tuple[set[str], set[str]]]
TagSets = Sequence[frozenset[str] | set[str]]


def as_tag_sets(rows: Iterable) -> list[frozenset[str]]:
    """Per-swipe tag collections as frozensets (missing data becomes the empty set)."""
    return [frozenset(d1.as_tag_set(r)) for r in rows]


def _side_flags(sets: TagSets, pairs: PolarityPairs) -> tuple[np.ndarray, np.ndarray]:
    """(n x G) indicators: the profile holds a tag of the `pos` / `neg` side of group g."""
    pos = np.array([[bool(s & p) for p, _ in pairs] for s in sets], dtype=bool)
    neg = np.array([[bool(s & n) for _, n in pairs] for s in sets], dtype=bool)
    return pos.reshape(len(sets), len(pairs)), neg.reshape(len(sets), len(pairs))


def _conflicts(
    s_flags: tuple[np.ndarray, np.ndarray], r_flags: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    (s_pos, s_neg), (r_pos, r_neg) = s_flags, r_flags
    return (s_pos & r_neg) | (s_neg & r_pos)


def group_conflicts(sender: TagSets, receiver: TagSets, pairs: PolarityPairs) -> np.ndarray:
    """(n x G) boolean: swipe i has a tag from opposite sides of group g on the two profiles."""
    return _conflicts(_side_flags(sender, pairs), _side_flags(receiver, pairs))


def prevalence_table(
    sender: TagSets, receiver: TagSets, pairs: PolarityPairs, mask: np.ndarray | None = None
) -> pd.DataFrame:
    """Per group (and `any`): conflict rate and how often a profile holds any tag of the group."""
    keep = np.ones(len(sender), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    s_flags, r_flags = _side_flags(sender, pairs), _side_flags(receiver, pairs)
    conf = _conflicts(s_flags, r_flags)[keep]
    s_any = (s_flags[0] | s_flags[1])[keep]
    r_any = (r_flags[0] | r_flags[1])[keep]
    rows = []
    for g, (pos, neg) in enumerate(pairs):
        rows.append(
            {
                "group": g,
                "pos": ",".join(sorted(pos)),
                "neg": ",".join(sorted(neg)),
                "n_conflicts": int(conf[:, g].sum()),
                "conflict_rate": float(conf[:, g].mean()),
                "sender_any_tag": float(s_any[:, g].mean()),
                "receiver_any_tag": float(r_any[:, g].mean()),
                "either_any_tag": float((s_any[:, g] | r_any[:, g]).mean()),
                "both_any_tag": float((s_any[:, g] & r_any[:, g]).mean()),
            }
        )
    rows.append(
        {
            "group": "any",
            "pos": "",
            "neg": "",
            "n_conflicts": int(conf.any(axis=1).sum()),
            "conflict_rate": float(conf.any(axis=1).mean()),
            "sender_any_tag": float(s_any.any(axis=1).mean()),
            "receiver_any_tag": float(r_any.any(axis=1).mean()),
            "either_any_tag": float((s_any.any(axis=1) | r_any.any(axis=1)).mean()),
            "both_any_tag": float((s_any.any(axis=1) & r_any.any(axis=1)).mean()),
        }
    )
    return pd.DataFrame(rows).set_index("group", drop=False).rename_axis(None)


def independence_baseline(
    sender: TagSets,
    receiver: TagSets,
    pairs: PolarityPairs,
    mask: np.ndarray | None = None,
    n_perm: int = 200,
    seed: int = 42,
    level: float = 0.95,
) -> dict[object, dict[str, float]]:
    """Conflict rate if the receiver's tag set were drawn independently of the sender.

    Receivers' tag sets are permuted between swipes (within `mask`); the permutation mean is the
    chance level, the central `level` band shows its spread. Keys: group index and `any`.
    """
    keep = np.ones(len(sender), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    s_pos, s_neg = (a[keep] for a in _side_flags(sender, pairs))
    r_pos, r_neg = (a[keep] for a in _side_flags(receiver, pairs))
    obs = _conflicts((s_pos, s_neg), (r_pos, r_neg))
    rng = np.random.default_rng(seed)
    sims = np.empty((n_perm, len(pairs) + 1))
    for b in range(n_perm):
        p = rng.permutation(len(s_pos))
        c = _conflicts((s_pos, s_neg), (r_pos[p], r_neg[p]))
        sims[b, :-1] = c.mean(axis=0)
        sims[b, -1] = c.any(axis=1).mean()
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    observed = [*obs.mean(axis=0), obs.any(axis=1).mean()]
    out: dict[object, dict[str, float]] = {}
    for j, key in enumerate([*range(len(pairs)), "any"]):
        out[key] = {
            "observed": float(observed[j]),
            "perm_mean": float(sims[:, j].mean()),
            "perm_lo": float(np.quantile(sims[:, j], lo_q)),
            "perm_hi": float(np.quantile(sims[:, j], hi_q)),
        }
    return out


def capture_tag_sets(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
    **variant: object,
) -> tuple[pd.DataFrame, list[frozenset[str]], list[frozenset[str]]]:
    """Build an H1 dataset (optionally a tag-decision variant) and return the per-swipe lifestyle
    tag sets of sender and receiver, row-aligned with the returned dataset."""
    sender: list[frozenset[str]] = []
    receiver: list[frozenset[str]] = []
    real = tv.make_conflict_fn

    def recording(pairs: PolarityPairs):
        fn = real(pairs)

        def conflict(a, b) -> int:
            sender.append(frozenset(d1.as_tag_set(a)))
            receiver.append(frozenset(d1.as_tag_set(b)))
            return fn(a, b)

        return conflict

    with mock.patch.object(tv, "make_conflict_fn", recording):
        df = tv.build_h1_variant(data_dir, docs_dir, **variant)
    return df, sender, receiver
