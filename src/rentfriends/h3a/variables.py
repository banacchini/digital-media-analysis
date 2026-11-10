"""Pure feature definitions for H3a (one profile snapshot -> numbers; no I/O)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from rentfriends.h3a.config import (
    AGE_BAND_INDEX,
    BIO_ALT_MIN_CHARS,
    BIO_CAP,
    CITY_UNKNOWN,
    EXTRA_TAG_MAP,
    LIFESTYLE_FIELDS,
    LIFESTYLE_FIELDS_ALT,
    TAG_CAP,
)


def bio_stripped_len(bio: pd.Series) -> pd.Series:
    """Length in characters of the stripped bio text; NULL counts as 0."""
    return bio.fillna("").astype(str).str.strip().str.len().astype(int)


def bio_empty(bio: pd.Series, min_chars: int = 1) -> pd.Series:
    """1 if the bio is NULL or shorter than `min_chars` after strip() (default: empty)."""
    return (bio_stripped_len(bio) < min_chars).astype(int)


def bio_features(bio: pd.Series, bio_length: pd.Series | None = None) -> pd.DataFrame:
    """Bio variables of the receiver: emptiness, length from text (G18), cap flag."""
    n = bio_stripped_len(bio)
    raw_len = bio.fillna("").astype(str).str.len()
    out = pd.DataFrame(
        {
            "bio_empty": (n < 1).astype(int),
            "bio_empty_alt10": (n < BIO_ALT_MIN_CHARS).astype(int),
            "bio_len": n,
            "bio_len_cap": (n >= BIO_CAP).astype(int),
        },
        index=bio.index,
    )
    out["has_bio"] = 1 - out["bio_empty"]
    if bio_length is not None:
        # G18 check: provider length vs length counted from the raw (unstripped) text.
        out["bio_length_mismatch"] = (bio_length.fillna(0).astype(int) != raw_len).astype(int)
    return out


def parse_tags(raw: str | None) -> list[str]:
    """Parse the jsonb `interests` string into a list of raw tag strings."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    tags = json.loads(raw)
    return [str(t) for t in tags] if isinstance(tags, list) else []


def build_tag_map(mapping: pd.DataFrame) -> dict[str, str]:
    """Raw tag string -> canonical slug, from interests_mapping.csv plus EXTRA_TAG_MAP."""
    m = dict(
        zip(mapping["original"].astype(str), mapping["canonical_tag"].astype(str), strict=True)
    )
    for k, v in EXTRA_TAG_MAP.items():
        m.setdefault(k, v)
    return m


def tag_counts(interests: pd.Series, tag_map: dict[str, str]) -> pd.DataFrame:
    """Raw tag count and effective count after mapping and within-user dedup (A3).

    Raw strings missing from the map keep their own string as slug (codebook B.1 rule).
    """
    parsed = interests.map(parse_tags)
    raw = parsed.map(len).astype(int)
    eff = parsed.map(lambda ts: len({tag_map.get(t, t) for t in ts})).astype(int)
    return pd.DataFrame(
        {
            "tag_count_raw": raw,
            "tag_count_receiver": eff,
            "tag_zero": (eff == 0).astype(int),
            "tag_cap": (eff >= TAG_CAP).astype(int),
        },
        index=interests.index,
    )


def completeness(df: pd.DataFrame, fields: list[str] | None = None) -> pd.Series:
    """Share of non-missing lifestyle fields (empty strings count as missing)."""
    fields = fields or LIFESTYLE_FIELDS
    present = pd.DataFrame(
        {f: df[f].astype("string").fillna("").str.strip().str.len() > 0 for f in fields},
        index=df.index,
    )
    return present.mean(axis=1)


def completeness_features(df: pd.DataFrame) -> pd.DataFrame:
    """`profile_completeness` (7 fields) and `profile_completeness_alt` (5 fields, S4)."""
    return pd.DataFrame(
        {
            "profile_completeness": completeness(df, LIFESTYLE_FIELDS),
            "profile_completeness_alt": completeness(df, LIFESTYLE_FIELDS_ALT),
        },
        index=df.index,
    )


def age_index(age_band: pd.Series) -> pd.Series:
    """Band index with 27+ merged (D9); NaN when the band is missing or unknown."""
    return age_band.map(AGE_BAND_INDEX).astype(float)


def sex_pair(sender_sex: pd.Series, receiver_sex: pd.Series) -> pd.Series:
    """Sender x receiver sex, `O` kept as its own level (9 cells, D8)."""
    s = sender_sex.astype("string")
    r = receiver_sex.astype("string")
    out = s + "→" + r
    return out.where(s.notna() & r.notna())


def same_city(sender_city: pd.Series, receiver_city: pd.Series) -> pd.Series:
    """'same' / 'different' / 'unknown' ('inne' or missing on either side)."""
    s = sender_city.astype("string")
    r = receiver_city.astype("string")
    unknown = s.isna() | r.isna() | (s == CITY_UNKNOWN) | (r == CITY_UNKNOWN)
    eq = (s == r).fillna(False).to_numpy(dtype=bool)
    out = pd.Series(np.where(eq, "same", "different"), index=s.index, dtype="object")
    out[unknown.fillna(True).to_numpy()] = "unknown"
    return out


# ----------------------------------------------------------------------------- bio quality (Z8)
# Descriptive, offline and rule-based; no text is returned or stored. The language rule is a
# crude stop-word heuristic and is NOT validated against a human gold standard.

_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0x2300, 0x23FF),
    (0x2190, 0x21FF),
)
_EMOJI_SKIP = set(range(0x1F3FB, 0x1F400)) | {0x200D, 0xFE0F, 0xFE0E, 0x20E3}

_PL_WORDS = frozenset(
    [
        "i",
        "w",
        "z",
        "na",
        "do",
        "się",
        "nie",
        "to",
        "jest",
        "że",
        "co",
        "jak",
        "ale",
        "lub",
        "czy",
        "mam",
        "lubię",
        "szukam",
        "jestem",
        "mieszkanie",
        "pokój",
        "studiuję",
        "studiuje",
        "mieszkania",
        "współlokatora",
        "współlokatorki",
        "osoba",
        "osobą",
        "dla",
        "przy",
        "po",
        "od",
        "bardzo",
        "też",
        "ja",
        "mnie",
        "mi",
        "moje",
        "cześć",
        "hej",
        "lubię",
        "kocham",
        "chcę",
        "chciałbym",
        "chciałabym",
        "spokojna",
        "spokojny",
        "otwarty",
        "otwarta",
    ]
)
_EN_WORDS = frozenset(
    [
        "i",
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "is",
        "am",
        "are",
        "my",
        "me",
        "for",
        "with",
        "on",
        "at",
        "it",
        "that",
        "this",
        "not",
        "but",
        "you",
        "your",
        "looking",
        "like",
        "love",
        "flat",
        "room",
        "roommate",
        "student",
        "studying",
        "looking",
        "hi",
        "hey",
        "open",
        "easy",
        "going",
        "friendly",
        "quiet",
        "clean",
        "want",
        "would",
    ]
)
_PL_DIACRITICS = frozenset("ąćęłńóśźż")


def count_emoji(text: str) -> int:
    """Number of emoji-range characters (modifiers, ZWJ and variation selectors not counted)."""
    n = 0
    for ch in text:
        cp = ord(ch)
        if cp in _EMOJI_SKIP:
            continue
        if any(lo <= cp <= hi for lo, hi in _EMOJI_RANGES):
            n += 1
    return n


def guess_language(text: str) -> str:
    """'pl' | 'en' | 'other' by stop-word and diacritic scores; 'other' also when unclear."""
    low = text.lower()
    letters = [c for c in low if c.isalpha()]
    if len(letters) < 12:
        return "other"
    words = [w.strip(".,!?;:()\"'") for w in low.split()]
    pl = sum(w in _PL_WORDS for w in words) + sum(c in _PL_DIACRITICS for c in low) / 2
    en = sum(w in _EN_WORDS for w in words)
    if pl == 0 and en == 0:
        return "other"
    return "pl" if pl > en else "en" if en > pl else "other"


def bio_quality(bio: pd.Series) -> pd.DataFrame:
    """Per-snapshot emoji count, number of '?' and language class (aggregates only downstream)."""
    text = bio.fillna("").astype(str)
    return pd.DataFrame(
        {
            "n_emoji": text.map(count_emoji).astype(int),
            "n_question": text.str.count(r"\?").astype(int),
            "lang": text.map(guess_language),
        },
        index=bio.index,
    )
