"""Slide-ready figure style and export helpers (PNG 300 dpi + SVG + aggregated CSV)."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

# Colour-blind-safe categorical palette (Okabe-Ito subset; checked with a CVD validator:
# all adjacent pairs dE >= 11 under protan/deutan/tritan, contrast >= 3:1 on white).
BLUE = "#0072B2"
VERMILION = "#D55E00"
GREEN = "#009E73"
GRAY = "#595959"
LIGHT = "#D5D2CB"
INK = "#0F0F0F"
PALETTE = [BLUE, VERMILION, GREEN]

FIGSIZE = (10, 5.6)


def apply_style() -> None:
    """One style for all H3a figures (16:9 slides, axis text >= 14 pt)."""
    mpl.rcParams.update(
        {
            "figure.figsize": FIGSIZE,
            "figure.dpi": 100,
            "savefig.dpi": 300,
            "font.size": 14,
            "axes.titlesize": 17,
            "axes.titleweight": "bold",
            "axes.labelsize": 15,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 13,
            "legend.frameon": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": GRAY,
            "axes.grid": True,
            "grid.color": LIGHT,
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def pl_decimal(ax, axis: str = "y") -> None:
    """Polish decimal comma on a linear axis."""
    from matplotlib.ticker import FuncFormatter

    fmt = FuncFormatter(lambda x, _: f"{x:g}".replace(".", ","))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


class FigureSaver:
    """Writes figures, their aggregated source data and a manifest row."""

    def __init__(self, report_dir: str | Path, version: str | None = None):
        self.dir = Path(report_dir)
        self.fig_dir = self.dir / "figures"
        self.data_dir = self.dir / "figure_data"
        self.tab_dir = self.dir / "tables"
        for d in (self.fig_dir, self.data_dir, self.tab_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.manifest = self.dir / "figures_manifest.csv"
        self.version = version or date.today().isoformat()
        self._rows: dict[str, list] = {}
        if self.manifest.exists():
            with self.manifest.open() as f:
                for row in list(csv.reader(f))[1:]:
                    self._rows[row[0]] = row

    def save_fig(
        self,
        fig: plt.Figure,
        name: str,
        data_df: pd.DataFrame,
        caption: str = "",
        model: str = "",
        n_swipes: int | None = None,
        n_receivers: int | None = None,
    ) -> None:
        """Save `fig` as PNG + SVG and `data_df` (already aggregated/suppressed) as CSV."""
        fig.savefig(self.fig_dir / f"{name}.png", dpi=300, bbox_inches="tight")
        fig.savefig(self.fig_dir / f"{name}.svg", bbox_inches="tight")
        data_df.to_csv(self.data_dir / f"{name}.csv", index=False)
        self._rows[name] = [
            name,
            f"figures/{name}.png|svg",
            caption,
            model,
            "" if n_swipes is None else n_swipes,
            "" if n_receivers is None else n_receivers,
            self.version,
        ]
        with self.manifest.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                ["id", "file", "caption_pl", "model_spec", "n_swipes", "n_receivers", "version"]
            )
            for r in sorted(self._rows.values()):
                w.writerow(r)

    def save_table(self, df: pd.DataFrame, name: str, floatfmt: str = ".4g") -> None:
        """Save a result table as CSV and Markdown."""
        df.to_csv(self.tab_dir / f"{name}.csv", index=False)
        (self.tab_dir / f"{name}.md").write_text(
            df.to_markdown(index=False, floatfmt=floatfmt) + "\n", encoding="utf-8"
        )


_saver: FigureSaver | None = None


def init(report_dir: str | Path, version: str | None = None) -> FigureSaver:
    global _saver
    apply_style()
    _saver = FigureSaver(report_dir, version)
    return _saver


def save_fig(fig: plt.Figure, name: str, data_df: pd.DataFrame, **kw) -> None:
    """Module-level shortcut required by the prompt: `save_fig(fig, name, data_df)`."""
    if _saver is None:
        raise RuntimeError("call figs.init(report_dir) first")
    _saver.save_fig(fig, name, data_df, **kw)
