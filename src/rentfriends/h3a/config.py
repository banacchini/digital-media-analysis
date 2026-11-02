"""Constants and defaults for the H3a analysis (see docs/prompts/h3a-notebook-prompt.md)."""

from __future__ import annotations

from pathlib import Path

SEED = 20261102
MARGIN = 0.10
DATA_DIR = Path("data/processed")
MAPPING_CSV = Path("docs/interests_mapping.csv")

LIFESTYLE_FIELDS = [
    "daily_routine",
    "lifestyle",
    "work_from_home",
    "cleanliness",
    "noise_level",
    "smoking",
    "alcohol",
]
# S4: cleanliness and noise_level may carry app defaults, so drop them from the denominator.
LIFESTYLE_FIELDS_ALT = [f for f in LIFESTYLE_FIELDS if f not in ("cleanliness", "noise_level")]

# Band index after merging 27+ (D9).
AGE_BAND_INDEX = {"18-20": 0, "21-23": 1, "24-26": 2, "27-30": 3, "31-35": 3, "36+": 3}
AGE_BAND_LABEL = {0: "18-20", 1: "21-23", 2: "24-26", 3: "27+"}

HYDERABAD = "Hyderabad"
CITY_UNKNOWN = "inne"
BIO_CAP = 250
BIO_ALT_MIN_CHARS = 10
TAG_CAP = 9

# Polish-label tag strings present in the data but absent from docs/interests_mapping.csv.
# Mapped to the canonical slug of their English emoji counterpart (D-H3a-6, agent default).
EXTRA_TAG_MAP = {
    "💻 Pracuję zdalnie": "works_remote",
    "🏃 Aktywność & sport": "active_sport",
    "🤫 Spokojne wieczory": "quiet_evenings",
    "🧵 DIY / rękodzieło": "diy",
}

# Minimum number of distinct users behind any published cell.
MIN_CELL_USERS = 5
