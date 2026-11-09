"""Figures for the graph analysis in STYLEGUIDE palette.

All figures:
- Primary series: purple #A247E3
- Comparison: blue #234CE0
- Baseline/null: gray #595959
- Highlight: pink #E95BD2
- Background: #F4F2EE
- Font: Plus Jakarta Sans (fallback: sans-serif)
- Always show uncertainty (intervals) and axis labels.
- No gradient fills inside plots.
- No user_key in any figure.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# STYLEGUIDE palette
_PURPLE = "#A247E3"
_BLUE = "#234CE0"
_GRAY = "#595959"
_PINK = "#E95BD2"
_BG = "#F4F2EE"
_BLACK = "#0F0F0F"

_FONT = "sans-serif"  # Plus Jakarta Sans not guaranteed; fallback gracefully

matplotlib.rcParams.update(
    {
        "font.family": _FONT,
        "axes.facecolor": _BG,
        "figure.facecolor": _BG,
        "axes.edgecolor": _GRAY,
        "axes.labelcolor": _BLACK,
        "xtick.color": _GRAY,
        "ytick.color": _GRAY,
        "text.color": _BLACK,
        "axes.grid": True,
        "grid.color": _GRAY,
        "grid.alpha": 0.2,
        "grid.linewidth": 0.8,
    }
)


def _save(fig: plt.Figure, path: Path, name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    fig.savefig(path / f"{name}.png", dpi=150, bbox_inches="tight", facecolor=_BG)
    fig.savefig(path / f"{name}.svg", bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    logger.info("Saved figure: %s", name)


# ---------------------------------------------------------------------------
# (a) Model ladder: logLoss reduction
# ---------------------------------------------------------------------------


def plot_model_ladder(
    model_names: list[str],
    logloss_values: list[float],
    logloss_lo: list[float],
    logloss_hi: list[float],
    baseline_logloss: float,
    out_dir: Path,
) -> None:
    """Relative logLoss reduction vs guessing baseline, with CI.

    Poster metric 1: "O ile mniej niepewności"
    """
    baseline = baseline_logloss
    reductions = [(baseline - ll) / baseline * 100 for ll in logloss_values]
    err_lo = [
        (baseline - lo) / baseline * 100 - r for lo, r in zip(logloss_lo, reductions, strict=False)
    ]
    err_hi = [
        r - (baseline - hi) / baseline * 100 for hi, r in zip(logloss_hi, reductions, strict=False)
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [_GRAY] + [_BLUE] * 1 + [_PURPLE] * (len(model_names) - 2)
    if len(colors) > len(model_names):
        colors = colors[: len(model_names)]

    ax.barh(
        model_names,
        reductions,
        xerr=[err_lo, err_hi],
        color=colors[: len(model_names)],
        capsize=4,
        height=0.5,
    )
    ax.axvline(0, color=_GRAY, linewidth=1, linestyle="--")
    ax.set_xlabel("Relative logLoss reduction vs baseline (%)")
    ax.set_title("O ile mniej niepewności – drabina modeli")
    fig.tight_layout()
    _save(fig, out_dir, "fig_model_ladder")


# ---------------------------------------------------------------------------
# (a) Calibration curve
# ---------------------------------------------------------------------------


def plot_calibration(
    bin_centers: np.ndarray,
    mean_pred: np.ndarray,
    mean_actual: np.ndarray,
    ci_lo: np.ndarray | None,
    ci_hi: np.ndarray | None,
    model_name: str,
    out_dir: Path,
) -> None:
    """Reliability diagram (poster metric 3)."""
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], color=_GRAY, linestyle="--", label="Idealnie skalibrowany")

    valid = ~np.isnan(mean_pred) & ~np.isnan(mean_actual)
    ax.scatter(mean_pred[valid], mean_actual[valid], color=_PURPLE, zorder=5, label=model_name)
    ax.plot(mean_pred[valid], mean_actual[valid], color=_PURPLE, alpha=0.6)

    if ci_lo is not None and ci_hi is not None:
        ax.fill_between(mean_pred[valid], ci_lo[valid], ci_hi[valid], alpha=0.2, color=_PURPLE)

    ax.set_xlabel("Średnie przewidywane prawdopodobieństwo")
    ax.set_ylabel("Obserwowana częstość polubień")
    ax.set_title(f"Kalibracja — {model_name}")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, f"fig_calibration_{model_name.lower().replace(' ', '_')}")


# ---------------------------------------------------------------------------
# (b) Observed vs expected matches
# ---------------------------------------------------------------------------


def plot_reciprocity_bars(
    bin_df: pd.DataFrame,
    out_dir: Path,
) -> None:
    """Poster metric 4: Observed vs expected matches by expected-probability bin."""
    if bin_df.empty:
        logger.warning("reciprocity bin_df empty; skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(bin_df))
    width = 0.35

    ax.bar(x - width / 2, bin_df["observed_matches"], width, color=_PURPLE, label="Obserwowane")
    ax.bar(x + width / 2, bin_df["expected_matches"], width, color=_BLUE, label="Oczekiwane")

    ax.set_xticks(x)
    ax.set_xticklabels(bin_df["expected_bin"], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Liczba matchy")
    ax.set_title("Obserwowane vs oczekiwane matche (wzajemność)")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, "fig_reciprocity_observed_vs_expected")


# ---------------------------------------------------------------------------
# (c) League curves
# ---------------------------------------------------------------------------


def plot_p_right_by_rank_diff(
    curve_df: pd.DataFrame,
    expected_curve: pd.DataFrame | None,
    out_dir: Path,
    name: str = "fig_league_p_right",
) -> None:
    """P(right swipe | rank difference) curve."""
    if curve_df.empty:
        logger.warning("rank diff curve empty; skipping %s", name)
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(
        curve_df["bin_mid"], curve_df["p_right"], color=_PURPLE, marker="o", label="Obserwowane"
    )
    ax.fill_between(
        curve_df["bin_mid"], curve_df["ci_lo"], curve_df["ci_hi"], alpha=0.2, color=_PURPLE
    )

    if expected_curve is not None and not expected_curve.empty:
        ax.plot(
            expected_curve["bin_mid"],
            expected_curve["p_right"],
            color=_GRAY,
            linestyle="--",
            label="Oczekiwane (p̂)",
        )

    ax.axhline(y=0, color=_GRAY, linewidth=0.5)
    ax.set_xlabel("Różnica percentylu pożądania (odbiorca − nadawca)")
    ax.set_ylabel("P(prawy swipe)")
    ax.set_title("Liga pożądania – P(prawy | różnica rangi)")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, name)


def plot_p_reciprocate_by_rank_diff(
    curve_df: pd.DataFrame,
    out_dir: Path,
) -> None:
    """P(B→A right | A→B right, rank difference) curve."""
    if curve_df.empty:
        logger.warning("reciprocate curve empty; skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(
        curve_df["bin_mid"],
        curve_df["p_reciprocate"],
        color=_PINK,
        marker="o",
        label="P(B→A prawo | A→B prawo)",
    )
    ax.fill_between(
        curve_df["bin_mid"], curve_df["ci_lo"], curve_df["ci_hi"], alpha=0.2, color=_PINK
    )
    ax.set_xlabel("Różnica percentylu pożądania (B − A)")
    ax.set_ylabel("P(wzajemność | A→B prawo)")
    ax.set_title("Wzajemność warunkowa – ligi pożądania")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, "fig_league_reciprocate")


# ---------------------------------------------------------------------------
# Lift@20% bar chart
# ---------------------------------------------------------------------------


def plot_lift_comparison(
    model_names: list[str],
    lift_values: list[float],
    out_dir: Path,
) -> None:
    """Poster metric 2: Lift@20% across models."""
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [_GRAY] + [_BLUE] + [_PURPLE] * max(0, len(model_names) - 2)
    ax.bar(model_names, lift_values, color=colors[: len(model_names)], width=0.5)
    ax.axhline(1.0, color=_GRAY, linestyle="--", label="Losowy wybór (lift=1)")
    ax.set_ylabel("Lift@20%")
    ax.set_title("Trafność wskazania 20% najlepszych profili")
    ax.legend()
    fig.tight_layout()
    _save(fig, out_dir, "fig_lift_at_20")
