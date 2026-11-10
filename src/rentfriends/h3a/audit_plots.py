"""Plots and tables for the audit results; read `audit_results.json` only (no model fits).

Change `kind`, labels or the selection of scenarios and re-run in seconds. Every figure also
writes its data as CSV next to it (aggregates only).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rentfriends.h3a import audit as AU

OUT_DIR = Path("reports/h3a/audit")
SECTIONS = {"z3": "z3_by_sender_sex", "z4": "z4", "z5": "z5"}


def scenario_table(res: dict | None = None, section: str = "z4") -> pd.DataFrame:
    """Rows (scenario x estimator) with OR and CIs for one section (z3 | z4 | z5)."""
    res = res or AU.load_audit()
    df = pd.DataFrame(res[SECTIONS.get(section, section)])
    cols = [
        "spec", "model", "estimator", "n_obs", "n_receivers", "or", "or_lo95", "or_hi95",
        "or_lo90", "or_hi90", "p", "label",
    ]  # fmt: skip
    return df[[c for c in cols if c in df.columns]]


def plot_scenarios(
    section: str = "z4",
    kind: str = "forest",  # "forest" | "dots" (point + 95% CI only, no 90%)
    res: dict | None = None,
    margin: float = 0.10,
    estimators: tuple[str, ...] | None = None,
    out_dir: Path = OUT_DIR,
    show: bool = False,
):
    """OR with 95% (thin) and 90% (thick) CI per scenario and estimator, log axis."""
    df = scenario_table(res, section).dropna(subset=["or"])
    if estimators:
        df = df[df["model"].isin(estimators)]
    df = df.reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 0.35 * len(df) + 1.5))
    ax.axvspan(np.exp(-margin), np.exp(margin), color="0.9", zorder=0)
    ax.axvline(1, color="0.4", lw=0.8)
    colors = {"M1_lme4": "tab:red", "M2": "tab:blue", "M3": "tab:green"}
    for i, r in df.iterrows():
        c = colors.get(r["model"], "k")
        ax.plot([r["or_lo95"], r["or_hi95"]], [i, i], color=c, lw=1)
        if kind == "forest":
            ax.plot([r["or_lo90"], r["or_hi90"]], [i, i], color=c, lw=3)
        ax.plot(r["or"], i, "o", color=c)
    ax.set_yticks(range(len(df)), [f"{r['spec']} ({r['model']})" for _, r in df.iterrows()])
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("OR prawego swipe'a: bio vs brak bio (szare pasmo = margines)")
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"audit_{section}_{kind}.png", dpi=150)
    df.to_csv(out_dir / f"audit_{section}_{kind}.csv", index=False)
    if show:
        plt.show()
    return fig, df
