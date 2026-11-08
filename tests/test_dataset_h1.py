"""Unit tests for H1 dataset preparation module."""

import numpy as np
import pandas as pd

from rentfriends.dataset_h1 import (
    AGE_BAND_MERGE,
    AGE_BAND_ORDER,
    apply_d13_tag_imputation,
    compute_lifestyle_tag_conflict,
    field_agreement_status,
    get_infrequent_canonical_tags,
    idf_weights,
    load_tag_mappings,
    load_user_idf,
    parse_raw_interests,
    resolve_as_of_profiles,
    smoking_direction,
    transform_and_disentangle_tags,
    user_tag_idf,
    weighted_jaccard,
)


def test_tag_mappings_and_transform():
    mapping_dict, category_dict, _ = load_tag_mappings(
        "docs/interests_mapping.csv",
        "docs/tag_category_proposal.csv",
    )
    assert len(mapping_dict) > 0
    assert "running" in category_dict or "board_games" in category_dict

    # Test parse raw
    assert parse_raw_interests("['running', 'camping']") == ["running", "camping"]
    assert parse_raw_interests(None) == []

    # Infrequent canonical tags
    s = pd.Series(["['running']", "['rare_tag']"])
    infreq = get_infrequent_canonical_tags(s, mapping_dict, min_samples=2)
    assert "rare_tag" in infreq
    assert "running" in infreq

    # Disentangle pure interests vs lifestyle vs status
    pure_interests, lifestyle_tags, status_tags = transform_and_disentangle_tags(
        "['running', 'smoker', 'student']",
        mapping_dict,
        category_dict,
        infrequent_tags=set(),
    )
    assert "running" in pure_interests
    assert "smoker" not in pure_interests
    assert "smoker" in lifestyle_tags
    assert "student" in status_tags


def test_d13_tag_imputation():
    df = pd.DataFrame(
        {
            "user_key": ["u1", "u2", "u3"],
            "smoking": [None, "Y", None],
            "lifestyle_tags": [["non_smoker"], ["smoker"], []],
        }
    )
    imputed = apply_d13_tag_imputation(df, lifestyle_tags_col="lifestyle_tags")
    assert imputed.loc[0, "smoking"] == "N"
    assert imputed.loc[1, "smoking"] == "Y"
    assert pd.isna(imputed.loc[2, "smoking"])


def test_age_band_merge_and_order():
    for band in ["27-30", "31-35", "36+"]:
        assert AGE_BAND_MERGE[band] == "27+"
    assert AGE_BAND_ORDER["27+"] == 3
    assert AGE_BAND_ORDER["18-20"] == 0


def test_lifestyle_tag_conflict():
    assert compute_lifestyle_tag_conflict(["smoker"], ["non_smoker"]) == 1
    assert compute_lifestyle_tag_conflict(["early_bird"], ["night_owl"]) == 1
    assert compute_lifestyle_tag_conflict(["early_bird"], ["early_bird"]) == 0
    assert compute_lifestyle_tag_conflict(["cooking"], ["reading"]) == 0


def test_resolve_as_of_profiles_logic():
    history = pd.DataFrame(
        {
            "user_key": ["u1", "u1", "u2"],
            "version": [1, 2, 1],
            "day": [10, 20, 15],
            "city": ["Wrocław", "Warszawa", "Kraków"],
            "sex": ["F", "F", "M"],
        }
    )
    users = pd.DataFrame(
        {
            "user_key": ["u1", "u2", "u3"],
            "city": ["Warszawa", "Kraków", "Gdańsk"],
            "sex": ["F", "M", "O"],
        }
    )
    query = pd.DataFrame(
        {
            "user_key": ["u1", "u1", "u2", "u3"],
            "day": [5, 25, 15, 10],
        }
    )

    res = resolve_as_of_profiles(
        query,
        history,
        users,
        user_col="user_key",
        day_col="day",
        prefix="actor_",
        profile_cols=["city", "sex"],
    )

    assert res.loc[0, "actor_source_flag"] == "first_version"
    assert res.loc[0, "actor_city"] == "Wrocław"

    assert res.loc[1, "actor_source_flag"] == "prior_version"
    assert res.loc[1, "actor_city"] == "Warszawa"

    assert res.loc[2, "actor_source_flag"] == "first_version"
    assert res.loc[2, "actor_city"] == "Kraków"

    assert res.loc[3, "actor_source_flag"] == "users_current"
    assert res.loc[3, "actor_city"] == "Gdańsk"
    assert res.loc[3, "actor_sex"] == "O"


def test_idf_weights_rare_tags_weigh_more():
    docs = [{"a", "b"}, {"a", "c"}, {"a"}, {"a", "b"}]
    w = idf_weights(docs, n_docs=4)
    assert w["a"] == 0.0  # in every document
    assert w["c"] > w["b"] > w["a"]
    assert np.isclose(w["c"], np.log(4 / 1))
    assert np.isclose(w["b"], np.log(4 / 2))


def test_weighted_jaccard_rare_overlap_counts_more_than_popular_overlap():
    w = {"popular": 0.1, "rare": 3.0, "x": 1.0, "y": 1.0}
    common_popular = weighted_jaccard({"popular", "x"}, {"popular", "y"}, w)
    common_rare = weighted_jaccard({"rare", "x"}, {"rare", "y"}, w)
    assert common_rare > common_popular
    assert weighted_jaccard({"x"}, {"x"}, w) == 1.0
    assert weighted_jaccard({"x"}, {"y"}, w) == 0.0
    assert weighted_jaccard(set(), set(), w) == 0.0
    # unseen tags get the maximal (rarest) weight instead of raising
    assert weighted_jaccard({"zzz"}, {"zzz"}, w, default_weight=3.0) == 1.0


def test_field_agreement_status_four_categories():
    s = pd.Series(["A", "A", None, None, "B"])
    r = pd.Series(["A", "B", "A", None, None])
    out = field_agreement_status(s, r)
    assert list(out) == ["agree", "disagree", "one_missing", "both_missing", "one_missing"]


def test_smoking_direction_is_asymmetric():
    s = pd.Series(["N", "V", "N", "V", "O", None, None])
    r = pd.Series(["V", "N", "N", "V", "V", "N", None])
    out = smoking_direction(s, r)
    assert list(out) == [
        "nonsmoker_to_user",
        "user_to_nonsmoker",
        "agree",
        "agree",
        "user_vs_other_user",
        "one_missing",
        "both_missing",
    ]


def test_user_tag_idf_excludes_hyderabad_and_returns_unseen_weight():
    users = pd.DataFrame(
        {
            "user_key": ["a", "b", "c", "h"],
            "pure_interests": [["x", "y"], ["x"], ["x", "z"], ["only_hyd"]],
        }
    )
    weights, unseen = user_tag_idf(users, hyderabad_users={"h"})
    assert "only_hyd" not in weights  # excluded accounts do not define the document set
    assert weights["x"] == 0.0  # all 3 remaining users have it
    assert np.isclose(weights["y"], np.log(3))
    assert np.isclose(unseen, np.log(3))  # rarest possible tag


def test_load_user_idf_finds_docs_next_to_data_when_run_from_another_directory(
    tmp_path, monkeypatch
):
    """Notebooks run from notebooks/, so the docs/ folder must be resolved from data_dir."""
    import shutil
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    (tmp_path / "docs").mkdir()
    for name in ("interests_mapping.csv", "tag_category_proposal.csv"):
        shutil.copy(repo / "docs" / name, tmp_path / "docs" / name)
    proc = tmp_path / "data" / "processed"
    proc.mkdir(parents=True)
    users = pd.DataFrame(
        {
            "user_key": ["a", "b", "h"],
            "city": ["Wrocław", "Warszawa", "Hyderabad"],
            "interests": ["['running']", "['running', 'camping']", "['camping']"],
        }
    )
    users.to_parquet(proc / "users.parquet")
    (tmp_path / "notebooks").mkdir()
    monkeypatch.chdir(tmp_path / "notebooks")

    weights, unseen = load_user_idf(proc)
    assert isinstance(weights, dict) and unseen > 0
