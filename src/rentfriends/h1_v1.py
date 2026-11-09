"""Data contract v1 for H1: the final tag-validation decisions (scenario vi) as a dataset.

v0 is the contract built with the agent's tag mapping (`h1_analysis_dataset.parquet`, never
overwritten). v1 swaps in the final human decisions: consensus A (raw -> canonical), consensus B
(category) and the merges of `docs/tag-validation/tag_merge_map.csv`, with D13 keys and D15
polarity groups re-pointed at the merge targets. Row set and schema are identical to v0.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rentfriends import dataset_h1 as d1
from rentfriends import h1_tagval as tv

V0_FILE = "h1_analysis_dataset.parquet"
V1_FILE = "h1_analysis_dataset_v1.parquet"
V1_SCENARIO = "vi"


def v1_inputs(
    docs_dir: str | Path = "docs", tagval_dir: str | Path = "docs/tag-validation"
) -> tuple[dict, dict]:
    """Arguments for `h1_tagval.build_h1_variant` (scenario vi) and the re-pointing audit."""
    docs, tag_dir = Path(docs_dir), Path(tagval_dir)
    base_map, _, _ = d1.load_tag_mappings(
        docs / "interests_mapping.csv", docs / "tag_category_proposal.csv"
    )
    scenario = next(s for s in tv.SCENARIOS if s.key == V1_SCENARIO)
    return tv.scenario_inputs(
        scenario,
        consensus_a=tv.load_consensus_a(tag_dir / "consensus_A.csv", base_map),
        consensus_b=tv.load_consensus_b(tag_dir / "consensus_B.csv"),
        merge=tv.load_merge_map(tag_dir / "tag_merge_map.csv"),
    )


def build_v0(
    data_dir: str | Path = "data/processed", docs_dir: str | Path = "docs"
) -> pd.DataFrame:
    """Contract v0 rebuilt from code (agent mapping)."""
    return d1.build_h1_dataset(data_dir=data_dir, docs_dir=docs_dir)


def build_v1(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
    tagval_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Contract v1 (final decisions: consensus A + B + merges)."""
    tag_dir = Path(docs_dir) / "tag-validation" if tagval_dir is None else tagval_dir
    kwargs, _ = v1_inputs(docs_dir, tag_dir)
    return tv.build_h1_variant(data_dir, docs_dir, **kwargs)


def write_v1(
    path: str | Path | None = None,
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
) -> Path:
    """Build v1 and write it; refuses to touch the v0 file."""
    target = Path(data_dir) / V1_FILE if path is None else Path(path)
    if target.name == V0_FILE:
        raise ValueError("refusing to overwrite the v0 contract file")
    build_v1(data_dir, docs_dir).to_parquet(target, index=False)
    return target


def load_v1(data_dir: str | Path = "data/processed") -> pd.DataFrame:
    """Read v1 and add the two city dummies that `h1.load_h1_data` adds for v0."""
    path = Path(data_dir) / V1_FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; build it with `write_v1`")
    return tv.with_city_dummies(pd.read_parquet(path))
