"""Tests for the post-audit H3a additions (label trace, scenarios, v1 tag map, new Spec fields)."""

import math

import numpy as np
import pandas as pd

from rentfriends.h3a import analysis as A
from rentfriends.h3a import audit as AU
from rentfriends.h3a import classify as C
from rentfriends.h3a import data as D
from rentfriends.h3a import models as M


def test_label_trace_matches_classify_for_published_m2():
    t = AU.label_trace(0.1221, 0.0402)
    assert t["label"] == C.classify(0.1221, 0.0402) == C.CONFIRMED
    # equivalence fails because the UPPER 90% limit (OR 1.207) exceeds exp(0.10) = 1.105
    assert not t["equiv_hi90_le_margin"] and t["equiv_lo90_ge_minus_margin"]
    assert t["sig_pos_lo95_gt_0"] and not t["lo95_above_margin"]


def test_label_trace_equivalence_and_inconclusive():
    assert AU.label_trace(0.01, 0.02)["label"] == C.PRACTICALLY_ZERO
    assert AU.label_trace(0.05, 0.10)["label"] == C.INCONCLUSIVE


def test_label_trace_agrees_with_classify_on_grid():
    for b in np.linspace(-0.4, 0.4, 17):
        for se in (0.01, 0.04, 0.1):
            assert AU.label_trace(b, se)["label"] == C.classify(b, se)


def _frame(n=40):
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "y_right": rng.integers(0, 2, n),
            "has_bio": rng.integers(0, 2, n),
            "age_band_diff": rng.integers(-2, 3, n),
            "same_band": rng.integers(0, 2, n),
            "profile_completeness": rng.random(n),
            "tag_count_receiver": rng.integers(0, 9, n),
            "tag_zero": rng.integers(0, 2, n),
            "tag_cap": rng.integers(0, 2, n),
            "sex_pair": rng.choice(["F→F", "F→M", "M→F", "M→M"], n),
            "same_city": rng.choice(["same", "different"], n),
            "act": rng.random(n),
        }
    )


def test_spec_age_h1_and_activity_columns():
    t = _frame()
    X, _ = M.build_design(t, M.Spec())
    assert "age_band_diff_abs" not in X.columns
    X1, _ = M.build_design(t, M.Spec(age_controls="h1", extra_controls=("act",)))
    assert {"same_band", "age_band_diff", "age_band_diff_abs", "act"} <= set(X1.columns)
    assert abs(X1["age_band_diff_abs"].mean()) < 1e-9


def test_default_spec_fingerprint_unchanged():
    d = A._spec_fp(M.Spec())
    assert "age_controls" not in d and "extra_controls" not in d
    assert "age_controls" in A._spec_fp(M.Spec(age_controls="h1"))


def test_tag_map_v1_applies_overrides_and_merges(tmp_path):
    (tmp_path / "consensus_A.csv").write_text(
        "raw_tag,runda1,canonical_tag,konsensus\nx_raw,a,a,b\ny_raw,c,c,c\n"
    )
    (tmp_path / "tag_merge_map.csv").write_text(
        "canonical_before,canonical_after,cluster,uzasadnienie\nb,m,k,u\nc,m,k,u\n"
    )
    mapping = pd.DataFrame({"original": ["x_raw", "y_raw"], "canonical_tag": ["a", "c"]})
    raw = D.RawData(None, None, None, mapping)
    tm = AU.tag_map_v1(raw, tmp_path)
    assert tm["x_raw"] == "m" and tm["y_raw"] == "m"  # override a->b, then merge b->m
    # two raw tags collapsing to one slug lower the effective count
    from rentfriends.h3a import variables as v

    out = v.tag_counts(pd.Series(['["x_raw","y_raw"]']), tm)
    assert out["tag_count_receiver"].iloc[0] == 1 and out["tag_count_raw"].iloc[0] == 2


def test_receiver_change_sets():
    h = pd.DataFrame(
        {
            "user_key": ["a", "a", "b", "b", "c"],
            "version": [0, 1, 0, 1, 0],
            "day": [0, 5, 0, 5, 0],
            "bio": ["", "hello", "hi", "hi there", "same"],
            "sex": "F", "age_band": "18-20", "city": "x", "daily_routine": "", "lifestyle": "",
            "work_from_home": "", "cleanliness": "", "noise_level": "", "smoking": "",
            "alcohol": "", "interests": "[]", "bio_length": [0, 5, 2, 8, 4],
        }
    )  # fmt: skip
    raw = D.RawData(None, h, None, None)
    ch = AU.receiver_change_sets(raw, {"a", "b", "c", "d"})
    assert ch["text"] == {"a", "b"} and ch["status"] == {"a"}
    assert math.isfinite(len(ch["text"]))
