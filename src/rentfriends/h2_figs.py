# ruff: noqa: E501
"""H2 figures. Every function only reads the result dict of `h2_audit.run_all` (the cache).

To change the look, edit `STYLE` or the functions here and re-run the plotting cell; nothing is
refitted. Palette from STYLEGUIDE.md: purple primary, blue comparison, gray null/baseline.
Each figure carries a one-sentence Polish caption (`CAPTIONS`) shown under the plot.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

STYLE = {
    "purple": "#A247E3",
    "purple_ink": "#8B34C4",
    "blue": "#234CE0",
    "gray": "#595959",
    "hair": "#D5D2CB",
    "ink": "#0F0F0F",
    "fontsize": 10,
    "dpi": 150,
}

CAPTIONS = {
    "sex_matrix": "Odsetek prawych swipe'ów według płci nadawcy i odbiorcy: wszyscy chętniej swipe'ują w prawo profile kobiet.",
    "sex_decomp": "Odbiorczynie vs odbiorcy w prawych swipe'ach: różnica jest duża u obu płci nadawców, ale u kobiet wyraźnie większa.",
    "age_matrix": "Odsetek prawych swipe'ów według pasma wieku nadawcy i odbiorcy; spada wraz z wiekiem odbiorcy u nadawców do 26 lat, a nadawcy 27+ swipe'ują podobnie we wszystkich pasmach; komórki z mniej niż 5 nadawcami byłyby ukryte.",
    "age_or": "Starszy odbiorca zmniejsza szansę na prawy swipe, młodszy niemal jej nie zmienia; OR na jedno pasmo różnicy.",
    "estimators": "Ten sam wpływ w dwóch estymatorach: populacyjny (pooled) jest bliżej 1 niż warunkowy (GLMM).",
    "cv_deltas": "Dodanie płci poprawia przewidywanie poza próbą wyraźnie, a wieku dodatkowo, ale umiarkowanie; przedziały z bootstrapu po nadawcach.",
    "bridge": "Skąd różnica OR wieku względem H1: zmiana próby i klastrów prawie nic nie zmienia, dopiero kontrole płci i miasta przesuwają OR ku 1.",
}


def _apply():
    plt.rcParams.update(
        {
            "font.size": STYLE["fontsize"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": STYLE["gray"],
            "axes.labelcolor": STYLE["ink"],
            "xtick.color": STYLE["gray"],
            "ytick.color": STYLE["gray"],
            "axes.grid": True,
            "grid.color": STYLE["hair"],
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "figure.dpi": 100,
        }
    )


def _caption(fig, key: str):
    fig.text(0.01, -0.07, CAPTIONS[key], ha="left", va="top", fontsize=8.5, color=STYLE["gray"])


def _or_axis(ax, lo: float, hi: float):
    ax.axvline(1, color=STYLE["gray"], ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlim(lo * 0.9, hi * 1.1)
    ticks = [t for t in (0.25, 0.35, 0.5, 0.75, 1, 1.5, 2, 3, 4) if lo * 0.9 <= t <= hi * 1.1]
    ax.set_xticks(ticks, [f"{t:g}".replace(".", ",") for t in ticks])
    ax.minorticks_off()


def _pct(r: float) -> str:
    return f"{r:.1%}".replace(".", ",")


def _n(x: float) -> str:
    return f"{int(x):,}".replace(",", "\u00a0")


def _pl_axis(ax, axis: str = "x"):
    """Decimal comma on a linear axis."""
    from matplotlib.ticker import FuncFormatter

    fmt = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "\u2212"))
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def _dot(ax, y, est, lo, hi, color, marker="o", hollow=False):
    ax.plot([lo, hi], [y, y], color=color, lw=1.8)
    ax.plot(
        est,
        y,
        marker,
        color="white" if hollow else color,
        mec=color,
        mew=1.6,
        ms=7,
    )


def sex_matrix(R: dict):
    _apply()
    m = R["z1_matrix"]
    sexes = ["F", "M", "O"]
    rates = m.pivot(index="sender_sex", columns="receiver_sex", values="rate").loc[sexes, sexes]
    ns = m.pivot(index="sender_sex", columns="receiver_sex", values="n").loc[sexes, sexes]
    cmap = LinearSegmentedColormap.from_list("one_hue", ["#FFFFFF", STYLE["purple_ink"]])
    fig, ax = plt.subplots(figsize=(5.2, 4))
    vmax = max(0.35, np.nanmax(rates.to_numpy(float)))
    im = ax.imshow(rates.to_numpy(float), cmap=cmap, vmin=0, vmax=vmax)
    ax.grid(False)
    ax.set_xticks(range(3), sexes)
    ax.set_yticks(range(3), sexes)
    ax.set_xlabel("płeć odbiorcy")
    ax.set_ylabel("płeć nadawcy")
    for i in range(3):
        for j in range(3):
            r = rates.iat[i, j]
            if pd.isna(r):
                continue
            ax.text(
                j,
                i,
                f"{_pct(r)}\nn={_n(ns.iat[i, j])}",
                ha="center",
                va="center",
                color="white" if r > 0.6 * vmax else STYLE["ink"],
                fontsize=9,
            )
    fig.colorbar(im, ax=ax, label="odsetek prawych", shrink=0.8)
    ax.set_title("Odsetek prawych swipe'ów", loc="left")
    _caption(fig, "sex_matrix")
    return fig


def sex_decomposition(R: dict, controls: bool = False):
    """Gaps per sender sex and the pi / h pair, pooled and (when it has SEs) GLMM."""
    _apply()
    d = R["z1_derived_controls" if controls else "z1_derived_bare"]
    quantities = [
        ("gap_F: odbiorca F vs M, nadawcy F", "kobiety → F vs M"),
        ("gap_M: odbiorca F vs M, nadawcy M", "mężczyźni → F vs M"),
        ("pi: popularność profili F (przy symetrii)", "π: popularność profili F*"),
        ("h: premia za własną płeć (przy symetrii)", "h: premia za własną płeć*"),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    cols = {"pooled (populacyjne)": STYLE["purple"], "GLMM (warunkowe)": STYLE["blue"]}
    for k, (q, _label) in enumerate(quantities):
        for j, (est, col) in enumerate(cols.items()):
            r = d[(d["quantity"] == q) & (d["estimator"] == est)]
            if r.empty:
                continue
            r = r.iloc[0]
            _dot(ax, k + (j - 0.5) * 0.28, r["or"], r["or_lo"], r["or_hi"], col)
    ax.set_yticks(range(len(quantities)), [q[1] for q in quantities])
    ax.invert_yaxis()
    _or_axis(ax, 0.9, 5)
    ax.set_xlabel("iloraz szans (skala log; 1 = brak różnicy); * przy założeniu symetrii")
    handles = [plt.Line2D([], [], color=c, lw=2, label=e) for e, c in cols.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    ax.set_title("Płeć odbiorcy a prawy swipe, według płci nadawcy", loc="left")
    _caption(fig, "sex_decomp")
    return fig


def age_matrix(R: dict):
    _apply()
    m = R["z2_matrix"]
    bands = ["18-20", "21-23", "24-26", "27+"]
    rates = m.pivot(index="sender_band", columns="receiver_band", values="rate").loc[bands, bands]
    ns = m.pivot(index="sender_band", columns="receiver_band", values="n").loc[bands, bands]
    lo = m.pivot(index="sender_band", columns="receiver_band", values="ci_low").loc[bands, bands]
    hi = m.pivot(index="sender_band", columns="receiver_band", values="ci_high").loc[bands, bands]
    cmap = LinearSegmentedColormap.from_list("one_hue", ["#FFFFFF", STYLE["purple_ink"]])
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    vmax = np.nanmax(rates.to_numpy(float))
    im = ax.imshow(rates.to_numpy(float), cmap=cmap, vmin=0, vmax=vmax)
    ax.grid(False)
    ax.set_xticks(range(4), bands)
    ax.set_yticks(range(4), bands)
    ax.set_xlabel("pasmo wieku odbiorcy")
    ax.set_ylabel("pasmo wieku nadawcy")
    for i in range(4):
        for j in range(4):
            r = rates.iat[i, j]
            if pd.isna(r):
                ax.text(
                    j,
                    i,
                    "ukryte\n(< 5 nadawców)",
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    color=STYLE["gray"],
                )
                continue
            txt = f"{_pct(r)}\n[{lo.iat[i, j]:.0%}; {hi.iat[i, j]:.0%}]\nn={_n(ns.iat[i, j])}"
            ax.text(
                j, i, txt, ha="center", va="center", fontsize=7.5,
                color="white" if r > 0.6 * vmax else STYLE["ink"],
            )  # fmt: skip
    fig.colorbar(im, ax=ax, label="odsetek prawych", shrink=0.8)
    ax.set_title("Prawe swipe'y: wiek nadawcy × wiek odbiorcy", loc="left")
    _caption(fig, "age_matrix")
    return fig


def age_or(R: dict):
    """Per-band OR of an older / younger receiver, with and without sender-band FE."""
    _apply()
    z = R["z2_models"]
    rows = []
    for fe in (0, 1):
        t = _terms(z[f"dir|fe={fe}"], f"dir|fe={fe}")
        t["fe"] = fe
        rows.append(t)
    t = pd.concat(rows)
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    labels = [
        ("older_per_band", "starszy odbiorca, na pasmo"),
        ("younger_per_band", "młodszy odbiorca, na pasmo"),
    ]
    styles = [
        ("pooled (populacyjne)", 0, STYLE["purple"], False),
        ("pooled (populacyjne)", 1, STYLE["purple"], True),
        ("GLMM (warunkowe)", 0, STYLE["blue"], False),
        ("GLMM (warunkowe)", 1, STYLE["blue"], True),
    ]
    for k, (term, _) in enumerate(labels):
        for j, (est, fe, col, hollow) in enumerate(styles):
            r = t[(t["term"] == term) & (t["estimator"] == est) & (t["fe"] == fe)]
            if r.empty or not np.isfinite(r.iloc[0]["or_lo"]):
                continue
            r = r.iloc[0]
            _dot(ax, k + (j - 1.5) * 0.18, r["or"], r["or_lo"], r["or_hi"], col, hollow=hollow)
    ax.set_yticks(range(2), [x[1] for x in labels])
    ax.invert_yaxis()
    _or_axis(ax, 0.4, 1.2)
    ax.set_xlabel("iloraz szans na prawy swipe (skala log)")
    handles = [
        plt.Line2D([], [], color=c, marker="o", mfc="white" if h else c, mec=c, lw=1.8,
                   label=f"{e.split(' ')[0]}{', FE pasma nadawcy' if h else ''}")
        for e, _, c, h in styles
    ]  # fmt: skip
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8)
    ax.set_title("Wiek odbiorcy względem nadawcy", loc="left")
    _caption(fig, "age_or")
    return fig


def _terms(est: dict, model: str) -> pd.DataFrame:
    from rentfriends.h2_audit import term_table

    return term_table(est, model)


def estimators(R: dict, controls: bool = False):
    """Pooled vs GLMM OR for the sex terms, side by side (Z3)."""
    _apply()
    tag = "controls" if controls else "bare"
    t = _terms(R[f"z1_fit_{tag}"]["pm"], "pm")
    t = t[t["term"].isin(["receiver_F", "sender_F:receiver_F"])]
    names = {
        "receiver_F": "π: odbiorca F (przy symetrii)",
        "sender_F:receiver_F": "h: premia za własną płeć",
    }
    fig, ax = plt.subplots(figsize=(7.4, 2.8))
    cols = {"pooled (populacyjne)": STYLE["purple"], "GLMM (warunkowe)": STYLE["blue"]}
    for k, term in enumerate(names):
        for j, (est, col) in enumerate(cols.items()):
            r = t[(t["term"] == term) & (t["estimator"] == est)]
            if r.empty:
                continue
            r = r.iloc[0]
            if np.isfinite(r["or_lo"]):
                _dot(ax, k + (j - 0.5) * 0.28, r["or"], r["or_lo"], r["or_hi"], col)
            else:  # point estimate only: GLMM without usable SEs
                ax.plot(r["or"], k + (j - 0.5) * 0.28, "x", color=col, ms=8)
    ax.set_yticks(range(len(names)), list(names.values()))
    ax.invert_yaxis()
    _or_axis(ax, 1, 5)
    ax.set_xlabel("iloraz szans (skala log); × = estymata bez błędu standardowego")
    handles = [plt.Line2D([], [], color=c, lw=2, label=e) for e, c in cols.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    _caption(fig, "estimators")
    return fig


def cv_deltas(R: dict):
    """Paired out-of-fold differences with sender-bootstrap CIs, two grouping schemes."""
    _apply()
    comps = ["sex vs null", "sex+age3 vs sex"]
    labels = {"sex vs null": "płeć vs brak cech", "sex+age3 vs sex": "+ wiek vs sama płeć"}
    metrics = [
        ("logloss", "Δ log loss (ujemna = lepiej)"),
        ("auc", "Δ AUC"),
        ("auc_pr", "Δ AUC-PR"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2))
    sch = {
        "sender": ("foldy po nadawcach", STYLE["purple"]),
        "receiver": ("foldy po odbiorcach", STYLE["blue"]),
    }
    for ax, (m, title) in zip(axes, metrics, strict=True):
        for k, c in enumerate(comps):
            for j, (g, (_, col)) in enumerate(sch.items()):
                de = R[f"z4_cv_{g}"]["deltas"]
                r = de[(de["comparison"] == c) & (de["metric"] == m)].iloc[0]
                _dot(ax, k + (j - 0.5) * 0.28, r["delta"], r["ci_low"], r["ci_high"], col)
        ax.axvline(0, color=STYLE["gray"], ls="--", lw=1)
        ax.set_yticks(range(len(comps)), [labels[c] for c in comps] if ax is axes[0] else [])
        ax.invert_yaxis()
        ax.set_title(title, loc="left", fontsize=9.5)
    for ax in axes:
        _pl_axis(ax)
    handles = [plt.Line2D([], [], color=c, lw=2, label=lab) for lab, c in sch.values()]
    fig.legend(
        handles=handles, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.06)
    )
    _caption(fig, "cv_deltas")
    return fig


def bridge(R: dict):
    """OR of 'older by 1 band' across the steps that separate the H2 model from H1."""
    _apply()
    b = R["z2_bridge"]
    terms = [("older_by_1", "starszy o 1 pasmo"), ("older_by_2plus", "starszy o 2+ pasma")]
    steps = list(dict.fromkeys(b["step"]))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.2), sharey=True)
    for ax, (term, title) in zip(axes, terms, strict=True):
        for k, s in enumerate(steps):
            r = b[(b["step"] == s) & (b["term"] == term)].iloc[0]
            _dot(
                ax, k, r["or"], r["or_lo"], r["or_hi"], STYLE["purple"] if k < 3 else STYLE["blue"]
            )
        _or_axis(ax, 0.25, 1.0)
        ax.set_title(title, loc="left", fontsize=9.5)
        ax.set_xlabel("OR (skala log)")
    axes[0].set_yticks(range(len(steps)), steps, fontsize=8)
    axes[0].invert_yaxis()
    _caption(fig, "bridge")
    return fig


def save_all(R: dict, out_dir: str | Path = "reports/h2/figures") -> list[Path]:
    """Render every figure to PNG (aggregates only)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    figs = {
        "sex_matrix": sex_matrix(R),
        "sex_decomp_bare": sex_decomposition(R, False),
        "sex_decomp_controls": sex_decomposition(R, True),
        "age_matrix": age_matrix(R),
        "age_or": age_or(R),
        "estimators": estimators(R),
        "cv_deltas": cv_deltas(R),
        "bridge": bridge(R),
    }
    paths = []
    for name, fig in figs.items():
        p = out / f"{name}.png"
        fig.savefig(p, dpi=STYLE["dpi"], bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(p)
    return paths
