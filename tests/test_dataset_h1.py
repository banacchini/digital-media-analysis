"""Unit tests for H1 dataset preparation module."""

import pandas as pd

from rentfriends.dataset_h1 import (
    AGE_BAND_MERGE,
    AGE_BAND_ORDER,
    apply_d13_tag_imputation,
    compute_lifestyle_tag_conflict,
    get_infrequent_canonical_tags,
    load_tag_mappings,
    parse_raw_interests,
    resolve_as_of_profiles,
    transform_and_disentangle_tags,
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
