"""Tests for the agent-side tag validation prep: hashes, blind sheets, determinism, usage sums."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from rentfriends import tagval_prep as tp

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TAGVAL = ROOT / "data" / "tagval"
PROCESSED = ROOT / "data" / "processed"

needs_data = pytest.mark.skipif(
    not (PROCESSED / "h1_analysis_dataset.parquet").exists(), reason="local data not available"
)


def _load_sheet_generator():
    spec = importlib.util.spec_from_file_location(
        "tagval_make_sheets", ROOT / "scripts" / "tagval_make_sheets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _annotation_rows(path: Path) -> list[tuple]:
    ws = load_workbook(path)["Adnotacje"]
    return [tuple(c.value for c in row) for row in ws.iter_rows()]


def _make_sheets(out_dir: Path, items: list[str], labels: list[str], annotators=("A", "B", "C")):
    gen = _load_sheet_generator()
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        a: gen.build("A", items, "raw_tag", labels, a, tp.SHEET_SEED, out_dir) for a in annotators
    }


ITEMS = [f"raw_{i:02d}" for i in range(40)]
CANON = [f"canon_{i:02d}" for i in range(12)]
LABELS = [*CANON, "brak"]


# --- hashes ------------------------------------------------------------------------------
def test_frozen_proposal_hash():
    assert tp.proposal_hash_ok(DOCS / "tag_category_proposal.csv")


def test_hash_mismatch_detected(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("canonical_tag\nx\n")
    assert not tp.proposal_hash_ok(f)


# --- blind sheets ------------------------------------------------------------------------
def test_sheets_have_only_allowed_columns_and_no_canonical_strings(tmp_path):
    paths = _make_sheets(tmp_path, ITEMS, LABELS)
    for path in paths.values():
        rows = _annotation_rows(path)
        assert rows[0] == ("item_id", "raw_tag", "etykieta", "uwagi")
        body = rows[1:]
        assert {r[1] for r in body} == set(ITEMS)  # key column holds raw items only
        assert all(r[2] is None and r[3] is None for r in body)  # nothing pre-filled
        all_text = {str(v) for r in rows for v in r if v is not None}
        assert not all_text & set(CANON)  # no canonical string anywhere in the annotation sheet


def test_sheets_same_items_different_orders(tmp_path):
    paths = _make_sheets(tmp_path, ITEMS, LABELS)
    bodies = {a: _annotation_rows(p)[1:] for a, p in paths.items()}
    assert len({frozenset((r[0], r[1]) for r in b) for b in bodies.values()}) == 1
    orders = {a: [r[1] for r in b] for a, b in bodies.items()}
    assert orders["A"] != orders["B"] != orders["C"] != orders["A"]


def test_sheets_deterministic(tmp_path):
    first = _make_sheets(tmp_path / "one", [*ITEMS], LABELS, annotators=("A",))
    second = _make_sheets(tmp_path / "two", [*ITEMS], LABELS, annotators=("A",))
    assert _annotation_rows(first["A"]) == _annotation_rows(second["A"])


@pytest.mark.skipif(not (TAGVAL / "sheets_A").exists(), reason="real sheets not generated")
def test_real_sheets_blind_and_complete():
    items = set(pd.read_csv(TAGVAL / "items_A.csv")["raw_tag"])
    agent = pd.read_csv(TAGVAL / "agent_A.csv")
    leaked = set(agent["canonical_tag"]) - items  # canonical strings that are not raw items
    sheets = sorted((TAGVAL / "sheets_A").glob("*.xlsx"))
    assert sheets
    for path in sheets:
        rows = _annotation_rows(path)
        assert rows[0] == ("item_id", "raw_tag", "etykieta", "uwagi")
        assert {r[1] for r in rows[1:]} == items
        assert all(r[2] is None and r[3] is None for r in rows[1:])
        assert not {str(v) for r in rows for v in r if v is not None} & leaked


@pytest.mark.skipif(not (TAGVAL / "canonical_labels.txt").exists(), reason="labels not generated")
def test_label_file_is_exactly_the_frozen_proposal_tags():
    labels = (TAGVAL / "canonical_labels.txt").read_text(encoding="utf-8").splitlines()
    proposal = pd.read_csv(DOCS / "tag_category_proposal.csv")["canonical_tag"]
    assert len(labels) == 68
    assert set(labels) == set(proposal)


# --- helpers on synthetic data -------------------------------------------------------------
def test_collect_raw_tags_and_agent_table():
    tags = tp.collect_raw_tags(["['a', 'b']", "['b']", None], ["['c']"])
    assert tags == ["a", "b", "c"]
    table = tp.agent_mapping_table(tags, {"a": "A", "b": "A"})
    assert list(table.columns) == ["raw_tag", "canonical_tag"]
    assert table["canonical_tag"].tolist() == ["A", "A", tp.NO_MATCH]


def test_emoji_form():
    assert tp.is_emoji_form("\U0001f3b5 music")
    assert not tp.is_emoji_form("music")


def test_tag_usage_counts_union_once_per_swipe():
    s = [frozenset({"a", "b"}), frozenset({"a"}), frozenset()]
    r = [frozenset({"a"}), frozenset({"c"}), frozenset({"c"})]
    out = tp.tag_usage(s, r, ["u1", "u1", "u2"], ["u3", "u4", "u4"], "raw_tag")
    got = out.set_index("raw_tag")
    assert got.loc["a", "n_swipes"] == 2  # swipe 1 has "a" on both sides: counted once
    assert got.loc["a", "n_profiles"] == 2  # u1 (sender) and u3 (receiver)
    assert got.loc["c", "n_swipes"] == 2
    assert got.loc["c", "n_profiles"] == 1  # u4 only
    assert got.loc["b", "n_swipes"] == 1


def test_tag_usage_canonical_merges_and_dedups():
    s = [frozenset({"a1", "a2"})]
    r = [frozenset({"zz"})]
    mapping = {"a1": "A", "a2": "A"}
    out = tp.tag_usage(
        s, r, ["u1"], ["u2"], "canonical_tag", transform=lambda t: mapping.get(t, tp.NO_MATCH)
    )
    got = out.set_index("canonical_tag")["n_swipes"].to_dict()
    assert got == {"A": 1, tp.NO_MATCH: 1}


def test_as_of_raw_tags_follow_d7_rules():
    history = pd.DataFrame(
        {
            "user_key": ["u1", "u1"],
            "day": [2, 6],
            "version": [1, 2],
            "interests": ["['a', 'b']", "['c']"],
        }
    )
    users = pd.DataFrame({"user_key": ["u1", "u2"], "interests": ["['c']", "['z']"]})
    sample = pd.DataFrame(
        {"user_key": ["u1", "u1", "u1"], "target_user_key": ["u2"] * 3, "day": [1, 4, 9]}
    )
    sender, receiver = tp.as_of_raw_tags(sample, history, users)
    assert sender == [frozenset({"a", "b"}), frozenset({"a", "b"}), frozenset({"c"})]
    assert receiver == [frozenset({"z"})] * 3  # u2 has no history: current profile


# --- real-data checksums -------------------------------------------------------------------
@needs_data
def test_usage_weights_match_h1_sample(tmp_path):
    stats = tp.run(data_dir=PROCESSED, docs_dir=DOCS, out_dir=tmp_path)
    assert stats["proposal_hash"] == "zgodny"
    assert stats["frozen_files_unchanged"] is True
    z4 = stats["z4"]
    assert z4["h1_sample_swipes"] == tp.EXPECTED["h1_sample_swipes"] == 92_754
    for key in ("raw_max_n_swipes", "canonical_max_n_swipes"):
        assert z4[key] <= z4["h1_sample_swipes"]
    assert z4["raw_tags_not_in_items_A"] == 0  # every raw string in the sample is an item

    raw = pd.read_csv(tmp_path / "tag_usage_raw.csv")
    canon = pd.read_csv(tmp_path / "tag_usage_canonical.csv")
    assert list(raw.columns) == ["raw_tag", "n_profiles", "n_swipes"]
    assert list(canon.columns) == ["canonical_tag", "n_profiles", "n_swipes"]
    assert len(raw) == z4["raw_rows"] and raw["n_swipes"].sum() == z4["raw_sum_n_swipes"]
    # merging raw strings into canonical tags can only lower the per-swipe tag count
    assert canon["n_swipes"].sum() <= raw["n_swipes"].sum()
    # determinism: a second run reproduces the files byte for byte
    again = tmp_path / "again"
    tp.run(data_dir=PROCESSED, docs_dir=DOCS, out_dir=again)
    for name in ("items_A.csv", "agent_A.csv", "tag_usage_raw.csv", "tag_usage_canonical.csv"):
        assert (tmp_path / name).read_bytes() == (again / name).read_bytes()
