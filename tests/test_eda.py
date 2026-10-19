from pathlib import Path

from rentfriends.EDA import (
    generate_all_visualizations,
    get_hypothesis_mappings,
    get_schema_relationships,
    join_table_schemas,
    parse_metadata_file,
)


def test_parse_metadata_file() -> None:
    metadata_path = Path("data/processed/metadata.txt")
    tables = parse_metadata_file(metadata_path)

    expected_tables = {"chats", "listings", "matches", "profile_history", "swipes", "users"}
    assert set(tables.keys()) == expected_tables

    # Check key columns
    assert "user_key" in tables["users"].columns
    assert "bio" in tables["users"].columns
    assert "direction" in tables["swipes"].columns
    assert "day" in tables["matches"].columns


def test_schema_relationships() -> None:
    rels = get_schema_relationships()
    assert len(rels) >= 10
    sources = {r.source_table for r in rels}
    assert "swipes" in sources
    assert "matches" in sources
    assert "chats" in sources


def test_join_table_schemas() -> None:
    metadata_path = Path("data/processed/metadata.txt")
    tables = parse_metadata_file(metadata_path)

    joined = join_table_schemas(
        tables["swipes"],
        tables["users"],
        left_on="user_key",
        right_on="user_key",
        joined_name="swipes_with_sender",
        suffixes=("", "_sender"),
    )
    assert joined.column_count > tables["swipes"].column_count
    assert "direction" in joined.columns
    assert "sex" in joined.columns


def test_hypothesis_mappings() -> None:
    mappings = get_hypothesis_mappings()
    assert len(mappings) == 5
    hyp_ids = {m.hypothesis_id for m in mappings}
    assert hyp_ids == {"H1", "H2", "H3", "H4", "H5"}


def test_generate_visualizations(tmp_path: Path) -> None:
    metadata_path = Path("data/processed/metadata.txt")
    figs = generate_all_visualizations(metadata_path, save_dir=tmp_path)
    assert len(figs) == 5
    for f in figs:
        assert f.exists()
        assert f.stat().st_size > 0
