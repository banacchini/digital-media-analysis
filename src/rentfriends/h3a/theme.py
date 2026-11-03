"""Shared visual theme for project figures (H3a story figures; reusable by H1/H2).

Usage:
    from rentfriends.h3a.theme import apply_theme, COLORS
    apply_theme()            # registers the local font and sets matplotlib rcParams

`reports/h3a/export/theme.json` is the machine-readable copy of the constants below.
Font files are read from `reports/assets/fonts` (already in the repo); nothing is downloaded.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager

FONT_DIR = Path("reports/assets/fonts")
FONT_FAMILY = "Plus Jakarta Sans"
FONT_FALLBACK = "DejaVu Sans"

# Okabe-Ito based; text colours are checked against white (>= 4.5:1).
COLORS = {
    "without_bio": "#6B7280",  # grey
    "with_bio": "#0072B2",  # blue
    "accent": "#D55E00",  # vermilion: markers, lines, highlights
    "accent_text": "#B34F00",  # darker vermilion for text (5.2:1 on white; #D55E00 is 3.9:1)
    "text": "#1F2937",
    "muted": "#E5E7EB",  # light grey: empty dots, bands
}

# Point sizes. Story figures are drawn on a 13.33 x 7.5 in canvas (16:9).
SIZES_PT = {"hero": 52, "title": 26, "label": 21, "small": 15, "min": 14}
CANVAS_IN = (13.33, 7.5)
MARGIN_IN = 0.6
EXPORT_DPI = 200


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast_ratio(fg: str, bg: str = "#FFFFFF") -> float:
    """WCAG contrast ratio of two hex colours."""
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def register_fonts(font_dir: Path = FONT_DIR) -> str:
    """Register the local font files and return the family to use (fallback if missing)."""
    files = sorted(font_dir.glob("PlusJakartaSans-*.ttf")) if font_dir.exists() else []
    for f in files:
        font_manager.fontManager.addfont(str(f))
    return FONT_FAMILY if files else FONT_FALLBACK


def apply_theme() -> str:
    """Set matplotlib rcParams for text-as-text SVG, the shared font and colours."""
    family = register_fonts()
    mpl.rcParams.update(
        {
            "font.family": [family, FONT_FALLBACK],
            "svg.fonttype": "none",
            "text.color": COLORS["text"],
            "axes.labelcolor": COLORS["text"],
            "xtick.color": COLORS["text"],
            "ytick.color": COLORS["text"],
            "axes.edgecolor": COLORS["without_bio"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "legend.frameon": False,
            "figure.dpi": 100,
        }
    )
    return family


def theme_dict() -> dict:
    return {
        "colors": COLORS,
        "font_family": FONT_FAMILY,
        "font_fallback": FONT_FALLBACK,
        "font_source": "reports/assets/fonts (local, SIL OFL)",
        "sizes_pt": SIZES_PT,
        "canvas_in": CANVAS_IN,
        "margin_in": MARGIN_IN,
        "export_dpi": EXPORT_DPI,
        "contrast_on_white": {k: round(contrast_ratio(v), 2) for k, v in COLORS.items()},
    }


def export_theme_json(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(theme_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
