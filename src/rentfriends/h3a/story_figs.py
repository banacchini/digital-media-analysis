"""Three plain-language H3a figures (A, B, C), plot only, for embedding in Typst.

All numbers come from `ctx.res["a5"]` (see `level3.a5_probs`); nothing is typed in by hand.
Exports `h3a_fig_{A,B,C}.svg|png` (+ `_preview.png` on white) to `<report_dir>/export/`.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

from rentfriends.h3a.theme import (
    CANVAS_IN,
    COLORS,
    EXPORT_DPI,
    SIZES_PT,
    apply_theme,
    contrast_ratio,
)

NBSP = " "
MINUS = "−"
PRACTICAL_ZERO_PP = 1.5  # visual reference band only; not the pre-registered verdict margin


def pl(x: float, nd: int = 1, sign: bool = False) -> str:
    """Polish number: decimal comma, proper minus sign."""
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s.replace(".", ",").replace("-", MINUS)


def pct(x: float, nd: int = 1) -> str:
    return f"{pl(x, nd)}%"


def pp(x: float, nd: int = 1, sign: bool = True) -> str:
    return f"{pl(x, nd, sign)}{NBSP}p.p."


def _rng(lo: float, hi: float, nd: int = 1) -> str:
    return f"{pl(lo, nd)}{NBSP}do{NBSP}{pl(hi, nd)}"


def _blank_canvas() -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=CANVAS_IN)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_IN[0])
    ax.set_ylim(0, CANVAS_IN[1])
    ax.axis("off")
    return fig, ax


# ============================================================================ figure A


def fig_a(a5: dict) -> plt.Figure:
    """Without bio vs with bio, two panels (female / male senders)."""
    apply_theme()
    fig = plt.figure(figsize=CANVAS_IN)
    gs = fig.add_gridspec(1, 2, left=0.09, right=0.975, top=0.84, bottom=0.17, wspace=0.22)
    ymax = 50.0
    panels = [("F", "Kobiety oceniają profile"), ("M", "Mężczyźni oceniają profile")]
    for k, (sx, title) in enumerate(panels):
        sp = a5["strata"][sx]
        ax = fig.add_subplot(gs[0, k])
        p0, p1 = sp["p0"]["pct"], sp["p1"]["pct"]
        d = sp["diff"]
        ax.set_xlim(0, 2)
        ax.set_ylim(0, ymax)
        x0, x1 = 0.55, 1.45
        ax.plot([x0], [p0], "o", ms=30, color=COLORS["without_bio"], zorder=3)
        ax.plot([x1], [p1], "o", ms=30, color=COLORS["with_bio"], zorder=3)
        ax.add_patch(
            FancyArrowPatch(
                (x0 + 0.17, p0 + (p1 - p0) * 0.12),
                (x1 - 0.17, p1 - (p1 - p0) * 0.12),
                arrowstyle="-|>",
                mutation_scale=42,
                lw=9,
                color=COLORS["with_bio"],
                alpha=0.55,
                zorder=2,
                shrinkA=0,
                shrinkB=0,
            )
        )
        ax.text(
            x0,
            p0 + 2.2,
            pct(p0),
            ha="center",
            va="bottom",
            fontsize=46,
            fontweight="bold",
            color=COLORS["without_bio"],
        )
        ax.text(
            x1,
            p1 + 2.2,
            pct(p1),
            ha="center",
            va="bottom",
            fontsize=46,
            fontweight="bold",
            color=COLORS["with_bio"],
        )
        ax.text(
            1.0,
            ymax * 0.97,
            pp(d["pct"]),
            ha="center",
            va="top",
            fontsize=SIZES_PT["hero"] * 0.8,
            fontweight="bold",
            color=COLORS["text"],
        )
        note = f"95%:{NBSP}{_rng(d['lo95'], d['hi95'])}{NBSP}p.p."
        ax.text(
            1.0,
            ymax * 0.97 - 6.4,
            note,
            ha="center",
            va="top",
            fontsize=SIZES_PT["small"] + 2,
            color=COLORS["text"],
        )
        if d["lo95"] < 0 < d["hi95"]:
            ax.text(
                1.0,
                ymax * 0.97 - 9.4,
                "przedział obejmuje zero",
                ha="center",
                va="top",
                fontsize=SIZES_PT["small"] + 2,
                color=COLORS["accent_text"],
                fontweight="bold",
            )
        ax.set_title(title, loc="left", fontsize=SIZES_PT["title"], fontweight="bold", pad=18)
        ax.set_xticks([x0, x1], ["bez bio", "z bio"], fontsize=SIZES_PT["label"] + 1)
        for lab, col in zip(
            ax.get_xticklabels(), (COLORS["without_bio"], COLORS["with_bio"]), strict=False
        ):
            lab.set_color(col)
            lab.set_fontweight("bold")
        ax.set_yticks([0, 10, 20, 30], [f"{v}%" for v in (0, 10, 20, 30)])
        ax.set_ylim(0, ymax)
        ax.tick_params(axis="y", labelsize=SIZES_PT["small"] + 1, length=0, colors=COLORS["text"])
        ax.tick_params(axis="x", length=0, pad=10)
        ax.spines["left"].set_color(COLORS["muted"])
        ax.spines["bottom"].set_color(COLORS["muted"])
        ax.spines["left"].set_linewidth(1.5)
        ax.spines["bottom"].set_linewidth(1.5)
    fig.text(
        0.09,
        0.02,
        "Odsetek prawych swipe'ów, oś od zera. Model uwzględnia płeć, wiek i miasto pary "
        "oraz kompletność profilu.",
        fontsize=SIZES_PT["small"],
        color=COLORS["text"],
        ha="left",
    )
    return fig


# ============================================================================ figure B


def _dot_grid(ax, value: float, color: str) -> None:
    """10 x 10 dots; `value` of 100 filled (the fractional dot is filled proportionally)."""
    full = int(math.floor(value + 1e-9))
    frac = value - full
    for i in range(100):
        row, col = divmod(i, 10)
        x, y = col, 9 - row
        ax.add_patch(Circle((x, y), 0.40, color=COLORS["muted"], lw=0))
        if i < full:
            ax.add_patch(Circle((x, y), 0.40, color=color, lw=0))
        elif i == full and frac > 0.02:
            ax.add_patch(Circle((x, y), 0.40, color=color, lw=0, alpha=max(frac, 0.2)))
    ax.set_xlim(-0.6, 9.6)
    ax.set_ylim(-0.6, 9.6)
    ax.set_aspect("equal")
    ax.axis("off")


def fig_b(a5: dict) -> plt.Figure:
    """Four 10 x 10 dot grids: right swipes per 100 (F/M x without/with bio)."""
    apply_theme()
    fig, base = _blank_canvas()
    gsize, inner, pair_gap, left = 2.55, 0.45, 1.25, 0.75
    xs = []
    x = left
    for _ in range(2):
        xs += [x, x + gsize + inner]
        x += 2 * gsize + inner + pair_gap
    ytop = 3.75  # grid bottom edge in canvas inches
    panels = [("F", "Kobiety oceniają profile"), ("M", "Mężczyźni oceniają profile")]
    cols = {"p0": COLORS["without_bio"], "p1": COLORS["with_bio"]}
    labels = {"p0": "bez bio", "p1": "z bio"}
    for pi, (sx, title) in enumerate(panels):
        sp = a5["strata"][sx]
        base.text(
            xs[2 * pi],
            6.95,
            title,
            fontsize=SIZES_PT["title"],
            fontweight="bold",
            color=COLORS["text"],
            va="center",
        )
        for qi, key in enumerate(("p0", "p1")):
            gx = xs[2 * pi + qi]
            ax = fig.add_axes(
                [gx / CANVAS_IN[0], ytop / CANVAS_IN[1], gsize / CANVAS_IN[0], gsize / CANVAS_IN[1]]
            )
            _dot_grid(ax, sp[key]["pct"], cols[key])
            cx = gx + gsize / 2
            base.text(
                cx,
                ytop + gsize + 0.1,
                labels[key],
                ha="center",
                va="bottom",
                fontsize=SIZES_PT["label"] + 1,
                fontweight="bold",
                color=cols[key],
            )
            base.text(
                cx,
                ytop - 0.18,
                pl(sp[key]["pct"]),
                ha="center",
                va="top",
                fontsize=SIZES_PT["hero"],
                fontweight="bold",
                color=cols[key],
            )
            base.text(
                cx,
                ytop - 1.12,
                f"95%:{NBSP}{_rng(sp[key]['lo95'], sp[key]['hi95'])}",
                ha="center",
                va="top",
                fontsize=SIZES_PT["small"] + 1,
                color=COLORS["text"],
            )
    base.text(
        CANVAS_IN[0] / 2,
        1.5,
        "100 swipe'ów na profile: kolorowe kropki to prawe swipe'y, szare to lewe.",
        ha="center",
        va="center",
        fontsize=SIZES_PT["label"] - 1,
        color=COLORS["text"],
    )
    return fig


# ============================================================================ figure C


def fig_c(a5: dict, rows_def: list[tuple[str, str]]) -> plt.Figure:
    """Robustness: effect in percentage points per specification (M2 average marginal effect)."""
    apply_theme()
    fig = plt.figure(figsize=CANVAS_IN)
    ax = fig.add_axes([0.37, 0.19, 0.60, 0.66])
    by = {r["spec"]: r for r in a5["by_spec"]}
    keys = [k for k, _ in rows_def if k in by]
    n = len(keys)
    zlo, zhi = -PRACTICAL_ZERO_PP, PRACTICAL_ZERO_PP
    ax.axvspan(zlo, zhi, color=COLORS["muted"], alpha=0.8, lw=0, zorder=0)
    ax.axvline(0, color=COLORS["without_bio"], lw=1.6, zorder=1)
    lows, highs = [zlo], [zhi]
    for i, k in enumerate(keys):
        y = n - 1 - i
        r = by[k]
        a = r["ame_m2"]
        ax.hlines(y, a["lo95_pp"], a["hi95_pp"], color=COLORS["with_bio"], lw=5, zorder=2)
        ax.plot(a["ame_pp"], y, "o", ms=15, color=COLORS["with_bio"], zorder=3)
        lows.append(a["lo95_pp"])
        highs.append(a["hi95_pp"])
        m3 = r.get("m3_pp")
        if m3:
            ax.plot(
                m3["pct"],
                y - 0.28,
                "D",
                ms=10,
                mfc="white",
                mec=COLORS["text"],
                mew=2.4,
                zorder=3,
            )
            lows.append(m3["lo95"])
            highs.append(m3["hi95"])
        if k == "S2a":
            ax.annotate(
                "połowa próby; efekt słabszy",
                xy=(a["hi95_pp"] + 0.1, y),
                xytext=(a["hi95_pp"] + 0.5, y + 0.02),
                va="center",
                fontsize=SIZES_PT["small"] + 1,
                color=COLORS["accent_text"],
                fontweight="bold",
            )
    ax.set_yticks(range(n))
    ax.set_yticklabels(
        [lbl for k, lbl in rows_def if k in by][::-1], fontsize=SIZES_PT["label"] - 1
    )
    ax.set_ylim(-0.7, n - 0.3)
    xlo = math.floor(min(lows) - 0.4)
    xhi = math.ceil(max(highs) + 0.4) + 5.6
    ax.set_xlim(xlo, xhi)
    ticks = [t for t in range(int(xlo), int(math.ceil(max(highs))) + 1) if t % 2 == 0]
    ax.set_xticks(ticks, [pl(t, 0) for t in ticks], fontsize=SIZES_PT["small"] + 1)
    ax.tick_params(axis="both", length=0, pad=8)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["muted"])
    ax.spines["bottom"].set_linewidth(1.5)
    ax.set_xlabel(
        "punkty procentowe: o ile częściej prawy swipe, gdy odbiorca ma bio",
        fontsize=SIZES_PT["label"] - 3,
        labelpad=10,
    )
    ax.text(
        0,
        n - 0.25,
        f"praktycznie{NBSP}zero{NBSP}(±{pl(PRACTICAL_ZERO_PP)}{NBSP}p.p.)",
        ha="center",
        va="bottom",
        fontsize=SIZES_PT["small"] + 1,
        color=COLORS["text"],
    )
    # direct key for the two markers (top row)
    y_top = n - 1
    first = by[keys[0]]
    ax.annotate(
        "kółko: wszyscy razem",
        xy=(first["ame_m2"]["hi95_pp"], y_top),
        xytext=(first["ame_m2"]["hi95_pp"] + 0.45, y_top + 0.05),
        va="center",
        fontsize=SIZES_PT["small"] + 1,
        color=COLORS["with_bio"],
        fontweight="bold",
    )
    if first.get("m3_pp"):
        ax.annotate(
            "romb: w obrębie jednej osoby",
            xy=(first["m3_pp"]["hi95"], y_top - 0.28),
            xytext=(max(first["m3_pp"]["hi95"], first["ame_m2"]["hi95_pp"]) + 0.45, y_top - 0.55),
            va="center",
            fontsize=SIZES_PT["small"] + 1,
            color=COLORS["text"],
        )
    fig.text(
        0.04,
        0.025,
        "Poziome kreski: przedział 95%. Pas: wartości praktycznie zerowe.",
        fontsize=SIZES_PT["small"],
        color=COLORS["text"],
    )
    return fig


# ============================================================================ export + checks


def check_fig(fig: plt.Figure, min_pt: float = 14.0, bg: str = "#FFFFFF") -> dict:
    """Programmatic checks: smallest font size and worst text-to-background contrast."""
    fig.canvas.draw()
    sizes, worst = [], 99.0
    bad = []
    for t in fig.findobj(plt.Text):
        if not t.get_text().strip() or not t.get_visible():
            continue
        sizes.append(t.get_fontsize())
        col = t.get_color()
        hexc = col if isinstance(col, str) and col.startswith("#") else None
        if hexc:
            cr = contrast_ratio(hexc, bg)
            worst = min(worst, cr)
            if cr < 4.5:
                bad.append((t.get_text()[:25], hexc, round(cr, 2)))
    return {
        "min_font_pt": min(sizes) if sizes else None,
        "font_ok": (min(sizes) >= min_pt) if sizes else True,
        "worst_contrast": None if worst == 99.0 else round(worst, 2),
        "low_contrast_texts": bad,
    }


def export_fig(fig: plt.Figure, name: str, out_dir: str | Path) -> dict:
    """SVG (text as text), PNG 200 dpi on transparent background, and a white-background preview."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    chk = check_fig(fig)
    fig.savefig(out / f"{name}.svg", transparent=True)
    fig.savefig(out / f"{name}.png", dpi=EXPORT_DPI, transparent=True)
    fig.savefig(out / f"{name}_preview.png", dpi=EXPORT_DPI, facecolor="white", transparent=False)
    plt.close(fig)
    return chk


def make_all(a5: dict, rows_def: list[tuple[str, str]], out_dir: str | Path) -> dict:
    return {
        "A": export_fig(fig_a(a5), "h3a_fig_A", out_dir),
        "B": export_fig(fig_b(a5), "h3a_fig_B", out_dir),
        "C": export_fig(fig_c(a5, rows_def), "h3a_fig_C", out_dir),
    }
