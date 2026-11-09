"""Data contract v1 (scenario vi): construction, determinism and v0 integrity."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from rentfriends import h1_v1
from rentfriends.tagval_prep import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
needs_data = pytest.mark.skipif(
    not (PROCESSED / "h1_analysis_dataset.parquet").exists(), reason="local data not available"
)


def test_v1_inputs_are_scenario_vi_from_the_final_decisions():
    kwargs, audit = h1_v1.v1_inputs(ROOT / "docs", ROOT / "docs" / "tag-validation")
    assert kwargs["tag_merge"]["going_out_friends"] == "often_out"
    assert len(kwargs["tag_merge"]) == 5
    assert kwargs["category_override"]["cooking"] == "lifestyle"  # consensus B, not the agent
    assert kwargs["raw_to_canonical_override"]  # consensus A overrides exist
    # D15 groups keep their number and both sides after the merge
    assert len(kwargs["polarity_pairs"]) == 5
    assert all(p and n for p, n in kwargs["polarity_pairs"])
    assert "likes_calm" in kwargs["polarity_pairs"][4][0]
    assert {r["tag"] for r in audit["d13_rekey"]} == {
        "quiet_evenings",
        "silence_after_22",
        "peace_and_quite",
    }


def test_contract_hashes_are_documented_and_match_the_files():
    contract = ROOT / "docs" / "data-contract-v1.md"
    if not contract.exists():
        pytest.skip("data contract v1 not written yet")
    text = contract.read_text(encoding="utf-8")
    for name in ("h1_analysis_dataset.parquet", "h1_analysis_dataset_v1.parquet"):
        path = PROCESSED / name
        if not path.exists():
            continue
        m = re.search(rf"`{re.escape(name)}`[^`]*`([0-9a-f]{{64}})`", text)
        assert m, f"hash of {name} missing in docs/data-contract-v1.md"
        assert m.group(1) == sha256_file(path), name


@needs_data
def test_v1_build_is_deterministic_and_leaves_v0_untouched(tmp_path):
    v0 = PROCESSED / "h1_analysis_dataset.parquet"
    v0_hash = sha256_file(v0)
    a, b = tmp_path / "a.parquet", tmp_path / "b.parquet"
    h1_v1.write_v1(a, PROCESSED, ROOT / "docs")
    h1_v1.write_v1(b, PROCESSED, ROOT / "docs")
    assert sha256_file(a) == sha256_file(b)
    assert sha256_file(v0) == v0_hash


@needs_data
def test_v0_rebuilds_from_code_and_v1_differs_only_in_tag_derived_columns():
    v0_stored = pd.read_parquet(PROCESSED / "h1_analysis_dataset.parquet")
    v0_code = h1_v1.build_v0(PROCESSED, ROOT / "docs")
    assert list(v0_code.columns) == list(v0_stored.columns)
    for col in v0_stored.columns:
        a, b = v0_code[col], v0_stored[col]
        if col.startswith("interests_set"):
            assert [list(x) for x in a] == [list(x) for x in b], col
        else:
            assert ((a == b) | (a.isna() & b.isna())).all(), col
    v1 = h1_v1.build_v1(PROCESSED, ROOT / "docs")
    assert list(v1.columns) == list(v0_stored.columns) and len(v1) == len(v0_stored)
    keys = ["user_key", "target_user_key", "day", "y_right", "sex_pair", "age_band_diff"]
    pd.testing.assert_frame_equal(v1[keys], v0_stored[keys])
    changed = sum(
        list(x) != list(y)
        for x, y in zip(v1["interests_set_sender"], v0_stored["interests_set_sender"], strict=True)
    )
    assert changed > 0
