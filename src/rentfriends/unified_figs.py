"""Figures for the unified block comparison (aggregates only, Polish labels).

Every ``fig_*`` function takes an aggregated DataFrame (see schemas in each docstring), returns a
matplotlib ``Figure`` and never calls ``plt.show()``. Empty or NaN input yields an empty-but-valid
figure. Colours are Okabe-Ito (colour-blind safe); blocks are also told apart by marker shape and
by row label, so the figures survive black-and-white printing.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from rentfriends.h3a.theme import FONT_FALLBACK, register_fonts

INK = "#0F0F0F"
GRAY = "#595959"
HAIR = "#D5D2CB"
BLUE = "#0072B2"
VERMILION = "#D55E00"
GREEN = "#009E73"
PINK = "#CC79A7"

MIN_CELL_N = 50

# block key -> (Polish label, colour, marker)
BLOCK_STYLE: dict[str, tuple[str, str, str]] = {
    "demography": ("Demografia", BLUE, "o"),
    "interests": ("Zainteresowania", VERMILION, "s"),
    "lifestyle": ("Styl życia", GREEN, "D"),
    "bio": ("Bio", PINK, "^"),
}
BLOCK_ORDER = list(BLOCK_STYLE)

LEVEL_LABELS = {
    "controls": "Kontrole",
    "only:demography": "Demografia",
    "demography": "Demografia",
    "dem+interests": "Demogr. + zainteresowania",
    "dem+lifestyle": "Demogr. + styl życia",
    "dem+bio": "Demogr. + bio",
    "full": "Pełny model",
}
LEVEL_ORDER = [
    "controls",
    "only:demography",
    "demography",
    "dem+interests",
    "dem+lifestyle",
    "dem+bio",
    "full",
]
SEX_LABELS = {"F": "K", "M": "M", "O": "inna"}
FIELD_LABELS = {
    "smoking": "Palenie",
    "pets": "Zwierzęta",
    "alcohol": "Alkohol",
    "parties": "Imprezy",
    "cleanliness": "Porządek",
    "sleep": "Rytm snu",
    "diet": "Dieta",
}


def apply_style() -> None:
    """Set the shared rcParams (STYLEGUIDE: white background, hairline grid, Plus Jakarta Sans)."""
    family = register_fonts()
    mpl.rcParams.update(
        {
            "font.family": [family, FONT_FALLBACK],
            "svg.fonttype": "none",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10.5,
            "legend.fontsize": 10,
            "legend.frameon": False,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.edgecolor": GRAY,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": HAIR,
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "figure.dpi": 100,
        }
    )


def _pl(x: float, digits: int = 3, sign: bool = False) -> str:
    """Format a number with a Polish decimal comma (and a real minus sign)."""
    if x is None or not np.isfinite(x):
        return "-"
    s = f"{x:{'+' if sign else ''}.{digits}f}".replace(".", ",").replace("-", "−")
    return s


def _tick_fmt(digits: int = 3, sign: bool = False):
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda v, _: _pl(v, digits, sign))


def _empty(fig: Figure, ax, msg: str = "Brak danych") -> Figure:
    ax.set_axis_off()
    ax.text(0.5, 0.5, msg, ha="center", va="center", color=GRAY, transform=ax.transAxes)
    return fig


def _need(df: pd.DataFrame | None, cols: list[str]) -> pd.DataFrame:
    """Return ``df`` restricted to rows, or an empty frame with the columns when absent."""
    if df is None or len(df) == 0 or not set(cols).issubset(df.columns):
        return pd.DataFrame(columns=cols)
    return df


def _block_meta(block: str) -> tuple[str, str, str]:
    return BLOCK_STYLE.get(block, (str(block), GRAY, "o"))


# ---------------------------------------------------------------------------
# 1. Main figure: own increments of each block
# ---------------------------------------------------------------------------


def fig_block_increments(contrasts: pd.DataFrame, null: pd.DataFrame) -> Figure:
    """Forest plot of the own AUC increment of each block (Fig. 2 of the preprint).

    contrasts: contrast, block, kind, d_auc, ci_lo, ci_hi (rows with kind == "unique" are used).
    null: block, base, null_mean, null_p95, observed_gain, p_perm.

    Two panels share the rows: the left one uses the full scale so that the dominant demography
    effect (+0.11) is shown honestly; the right one zooms into [-0.004, +0.008] (a zoom, not an
    axis break, so no distances are distorted) where the three small blocks and the permutation
    null band can be told apart. Demography lies off the zoomed scale and is marked with an arrow.
    The null band is the permutation null of the gain over demography (null_mean .. null_p95), drawn
    per block where available.
    """
    apply_style()
    c = _need(contrasts, ["block", "kind", "d_auc", "ci_lo", "ci_hi"])
    c = c[c["kind"] == "unique"].dropna(subset=["d_auc"])
    c = c.assign(_o=c["block"].map({b: i for i, b in enumerate(BLOCK_ORDER)}).fillna(99))
    c = c.sort_values("_o").reset_index(drop=True)
    nl = _need(null, ["block", "null_mean", "null_p95"]).set_index("block", drop=False)

    fig = Figure(figsize=(10, 4.6), layout="constrained")
    if c.empty:
        return _empty(fig, fig.add_subplot())
    axl, axr = fig.subplots(1, 2, sharey=True, gridspec_kw={"width_ratios": [1, 1.35]})
    n = len(c)
    ys = np.arange(n)[::-1]
    zoom = (-0.004, 0.008)

    for ax in (axl, axr):
        ax.axvline(0, color=INK, lw=1.0, zorder=2)
        ax.grid(axis="y", visible=False)
        for y, (_, r) in zip(ys, c.iterrows(), strict=True):
            if r["block"] in nl.index:
                lo, hi = nl.loc[r["block"], ["null_mean", "null_p95"]].astype(float)
                if np.isfinite(lo) and np.isfinite(hi):
                    ax.add_patch(
                        Rectangle(
                            (lo, y - 0.38),
                            hi - lo,
                            0.76,
                            facecolor="#E5E7EB",
                            edgecolor=GRAY,
                            hatch="////",
                            lw=0.5,
                            zorder=1,
                        )
                    )
    for y, (_, r) in zip(ys, c.iterrows(), strict=True):
        label, colour, marker = _block_meta(r["block"])
        for ax in (axl, axr):
            lo, hi = r["ci_lo"], r["ci_hi"]
            if np.isfinite(lo) and np.isfinite(hi):
                ax.hlines(y, lo, hi, color=colour, lw=2.2, zorder=3)
            ax.plot(
                r["d_auc"],
                y,
                marker=marker,
                ms=9,
                color=colour,
                mec="white",
                mew=1.2,
                ls="none",
                zorder=4,
            )
        off = not (zoom[0] <= r["d_auc"] <= zoom[1])
        dg = 3 if abs(r["d_auc"]) >= 0.01 else 4
        txt = _pl(r["d_auc"], dg, True)
        if np.isfinite(r["ci_lo"]) and np.isfinite(r["ci_hi"]):
            txt += f"  [{_pl(r['ci_lo'], dg)}; {_pl(r['ci_hi'], dg)}]"
        if off:
            txt = "poza skalą (→): " + txt
            axr.annotate(
                "",
                xy=(zoom[1], y),
                xytext=(zoom[1] - 0.0007, y),
                arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 2},
                zorder=5,
            )
        axr.text(
            zoom[0] + 0.0001, y + 0.42, txt, ha="left", va="bottom", fontsize=9, color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0}, zorder=6,
        )  # fmt: skip

    axl.set_yticks(ys)
    axl.set_yticklabels([_block_meta(b)[0] for b in c["block"]])
    axl.set_ylim(-0.7, n - 0.3 + 0.35)
    axr.set_xlim(*zoom)
    axl.set_xlim(-0.01, 0.15)
    axl.set_title("Pełna skala", loc="left")
    axr.set_title("Powiększenie wokół zera", loc="left")
    for ax in (axl, axr):
        ax.set_xlabel("Przyrost własny AUC (pełny model − pełny bez bloku)")
    axl.xaxis.set_major_formatter(_tick_fmt(2))
    axr.xaxis.set_major_formatter(_tick_fmt(3))
    handles = [
        Rectangle((0, 0), 1, 1, facecolor="#E5E7EB", edgecolor=GRAY, hatch="////", lw=0.5),
    ]
    fig.legend(
        handles,
        ["Null z permutacji (średnia do 95. percentyla)"],
        loc="outside lower center",
        ncols=1,
    )
    fig.suptitle(
        "Demografia dominuje; pozostałe bloki dodają ułamki punktu AUC",
        x=0.01,
        ha="left",
        fontweight="bold",
        fontsize=13,
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Levels
# ---------------------------------------------------------------------------


def fig_levels(levels: pd.DataFrame) -> Figure:
    """AUC (mean over folds, +- 1 SD over folds) of the nested models.

    levels: model, auc_fold_mean, auc_fold_sd, auc_pooled, logloss, n_params.
    Only controls, demography, demography + one block, and the full model are shown.
    """
    apply_style()
    d = _need(levels, ["model", "auc_fold_mean", "auc_fold_sd"])
    d = d[d["model"].isin(LEVEL_ORDER)].dropna(subset=["auc_fold_mean"])
    d = d.assign(_o=d["model"].map({m: i for i, m in enumerate(LEVEL_ORDER)}))
    d = d.sort_values("_o").drop_duplicates("model")
    fig = Figure(figsize=(8, 4.2), layout="constrained")
    ax = fig.add_subplot()
    if d.empty:
        return _empty(fig, ax)
    ys = np.arange(len(d))[::-1]
    colours = {
        "controls": GRAY,
        "only:demography": BLUE,
        "demography": BLUE,
        "dem+interests": VERMILION,
        "dem+lifestyle": GREEN,
        "dem+bio": PINK,
        "full": INK,
    }
    markers = {"dem+interests": "s", "dem+lifestyle": "D", "dem+bio": "^", "full": "P"}
    ax.axvline(0.5, color=GRAY, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(0.5, -0.55, " losowo = 0,5", color=GRAY, fontsize=9, va="bottom")
    for y, (_, r) in zip(ys, d.iterrows(), strict=True):
        sd = r["auc_fold_sd"] if np.isfinite(r.get("auc_fold_sd", np.nan)) else 0.0
        col = colours.get(r["model"], GRAY)
        ax.errorbar(
            r["auc_fold_mean"],
            y,
            xerr=sd,
            fmt=markers.get(r["model"], "o"),
            color=col,
            ms=9,
            mec="white",
            mew=1.2,
            lw=2,
            capsize=3,
            zorder=3,
        )
        ax.text(
            0.995, y, _pl(r["auc_fold_mean"], 3), va="center", ha="right", fontsize=10,
            transform=ax.get_yaxis_transform(),
        )  # fmt: skip
    ax.set_yticks(ys)
    ax.set_yticklabels([LEVEL_LABELS.get(m, m) for m in d["model"]])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("AUC (średnia z foldów ± 1 odch. std.)")
    ax.xaxis.set_major_formatter(_tick_fmt(2))
    ax.set_ylim(-0.6, ys.max() + 1.0)
    ax.set_xlim(min(0.45, float(d["auc_fold_mean"].min()) - 0.03), 0.70)
    ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(0.05))
    ax.set_title("Poziomy AUC modeli zagnieżdżonych", loc="left")
    return fig


# ---------------------------------------------------------------------------
# 3. Sensitivity
# ---------------------------------------------------------------------------


def fig_sensitivity(sens: pd.DataFrame) -> Figure:
    """Own increments of each block across scenarios: one small multiple per block.

    sens: scenario, n_swipes, block, d_auc, ci_lo, ci_hi. Each panel has its own x scale
    (the demography effect is ~50x larger than the others); the zero line is drawn in every panel.
    """
    apply_style()
    s = _need(sens, ["scenario", "block", "d_auc", "ci_lo", "ci_hi"])
    s = s.dropna(subset=["d_auc"])
    blocks = [b for b in BLOCK_ORDER if b in set(s["block"])] + sorted(
        set(s["block"]) - set(BLOCK_ORDER)
    )
    fig = Figure(figsize=(10.5, 4.2), layout="constrained")
    if s.empty:
        return _empty(fig, fig.add_subplot())
    scen = list(dict.fromkeys(s["scenario"]))
    nsw = (
        s.drop_duplicates("scenario").set_index("scenario")["n_swipes"]
        if "n_swipes" in s
        else pd.Series(dtype=float)
    )
    axes = fig.subplots(1, len(blocks), sharey=True, squeeze=False)[0]
    ys = np.arange(len(scen))[::-1]
    for ax, b in zip(axes, blocks, strict=True):
        label, colour, marker = _block_meta(b)
        sub = s[s["block"] == b].set_index("scenario")
        ax.axvline(0, color=INK, lw=1, zorder=2)
        ax.grid(axis="y", visible=False)
        for y, sc in zip(ys, scen, strict=True):
            if sc not in sub.index:
                continue
            r = sub.loc[sc]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            if np.isfinite(r["ci_lo"]) and np.isfinite(r["ci_hi"]):
                ax.hlines(y, r["ci_lo"], r["ci_hi"], color=colour, lw=2, zorder=3)
            ax.plot(r["d_auc"], y, marker, ms=8, color=colour, mec="white", mew=1, zorder=4)
        ax.set_title(label, loc="left")
        ax.xaxis.set_major_formatter(_tick_fmt(3))
        ax.tick_params(axis="x", labelsize=8.5)
        ax.locator_params(axis="x", nbins=3)
        ax.set_xlabel("Przyrost własny AUC", fontsize=9.5)
    axes[0].set_yticks(ys)
    ylab = [
        f"{sc} (n={int(nsw[sc]):,})".replace(",", " ") if sc in nsw and np.isfinite(nsw[sc]) else sc
        for sc in scen
    ]
    axes[0].set_yticklabels(ylab, fontsize=9.5)
    axes[0].set_ylim(-0.6, len(scen) - 0.4)
    fig.suptitle(
        "Czułość przyrostów własnych bloków na scenariusze (95% przedziały)",
        x=0.01, ha="left", fontweight="bold", fontsize=13,
    )  # fmt: skip
    return fig


# ---------------------------------------------------------------------------
# 4. Sex matrix
# ---------------------------------------------------------------------------


def fig_sex_matrix(matrix: pd.DataFrame) -> Figure:
    """Right-swipe rate per sender sex x receiver sex cell, with intervals.

    matrix: sender_sex, receiver_sex, n, rate, ci_lo, ci_hi, wilson_lo, wilson_hi.
    Cells with n < 50 are drawn hollow and grey, labelled "n<50", and are not to be interpreted.
    """
    apply_style()
    m = _need(matrix, ["sender_sex", "receiver_sex", "n", "rate"]).dropna(subset=["rate"])
    fig = Figure(figsize=(8, 4.6), layout="constrained")
    ax = fig.add_subplot()
    if m.empty:
        return _empty(fig, ax)
    m = m.sort_values(["sender_sex", "receiver_sex"]).reset_index(drop=True)
    ys = np.arange(len(m))[::-1]
    sender_col = {"F": VERMILION, "M": BLUE}
    sender_mark = {"F": "o", "M": "s"}
    for y, (_, r) in zip(ys, m.iterrows(), strict=True):
        small = r["n"] < MIN_CELL_N
        col = GRAY if small else sender_col.get(r["sender_sex"], GREEN)
        mk = "^" if small else sender_mark.get(r["sender_sex"], "D")
        lo = (
            r["ci_lo"]
            if "ci_lo" in m and np.isfinite(r.get("ci_lo", np.nan))
            else r.get("wilson_lo", np.nan)
        )
        hi = (
            r["ci_hi"]
            if "ci_hi" in m and np.isfinite(r.get("ci_hi", np.nan))
            else r.get("wilson_hi", np.nan)
        )
        if np.isfinite(lo) and np.isfinite(hi):
            ax.hlines(y, lo, hi, color=col, lw=2, ls=(0, (2, 2)) if small else "-", zorder=3)
        ax.plot(
            r["rate"], y, mk, ms=9, color="white" if small else col, mec=col, mew=1.8, zorder=4,
        )  # fmt: skip
        note = "  n<50: bez wniosków" if small else ""
        x_txt = hi if np.isfinite(hi) else r["rate"]
        label_txt = f"{r['rate'] * 100:.0f}% (n={int(r['n']):,}){note}"
        ax.text(
            x_txt + 0.01, y, label_txt.replace(",", "\u00a0"),
            va="center", fontsize=9.5, color=GRAY if small else INK,
        )  # fmt: skip
    ax.set_yticks(ys)
    ax.set_yticklabels(
        [
            f"{SEX_LABELS.get(a, a)} → {SEX_LABELS.get(b, b)}"
            for a, b in zip(m["sender_sex"], m["receiver_sex"], strict=True)
        ]
    )
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 1.05 * max(0.3, float(np.nanmax(m.get("ci_hi", m["rate"])) + 0.35)))
    ax.set_xlim(0, min(1.2, ax.get_xlim()[1]))
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_xlabel("Odsetek prawych swipe'ów (przedział 95%)")
    ax.set_ylabel("płeć nadawcy → płeć odbiorcy")
    ax.set_title("Prawe swipe'y według płci pary", loc="left")
    return fig


# ---------------------------------------------------------------------------
# 5. Lifestyle missingness
# ---------------------------------------------------------------------------


def fig_lifestyle_missing(lifestyle_missing: pd.DataFrame) -> Figure:
    """Bars of the share of known lifestyle fields.

    lifestyle_missing: field, share_known (0..1); the columns `pole` and
    `odsetek_znanych_po_d13` of `unified.descriptives` are accepted too.
    """
    apply_style()
    lm = lifestyle_missing
    if lm is not None:  # accept the output of `unified.descriptives` as is
        lm = lm.rename(columns={"pole": "field", "odsetek_znanych_po_d13": "share_known"})
    d = _need(lm, ["field", "share_known"]).dropna(subset=["share_known"])
    fig = Figure(figsize=(7.5, 4.2), layout="constrained")
    ax = fig.add_subplot()
    if d.empty:
        return _empty(fig, ax)
    d = d.sort_values("share_known").reset_index(drop=True)
    ys = np.arange(len(d))
    ax.barh(ys, d["share_known"], color=GRAY, height=0.6, zorder=3)
    for y, v in zip(ys, d["share_known"], strict=True):
        ax.text(v + 0.01, y, f"{v * 100:.0f}%", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([FIELD_LABELS.get(f, f) for f in d["field"]])
    ax.set_xlim(0, 1.0)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_xlabel("Odsetek znanych wartości pola")
    ax.set_title("Kompletność pól stylu życia", loc="left")
    return fig


# ---------------------------------------------------------------------------
# 6. Save
# ---------------------------------------------------------------------------


def save(fig: Figure, name: str, out_dir: str | Path = "reports/figures") -> list[Path]:
    """Write ``<name>.png`` (200 dpi) and ``<name>.svg`` without path metadata; return the paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, meta in (("png", {"Software": None}), ("svg", {"Date": None, "Creator": None})):
        p = out / f"{name}.{ext}"
        fig.savefig(p, dpi=200, format=ext, metadata=meta, facecolor="white")
        paths.append(p)
    return paths
