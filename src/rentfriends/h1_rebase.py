"""H1 on data contract v1: CIs for block increments and dictionary sensitivity (post hoc).

Block increments (log-likelihood gains of the age, interests and lifestyle blocks) are summarised
over cluster-bootstrap replicates of the 8 nested models (`h1_audit.bootstrap_model_loglik`).
Replicates of different tag dictionaries use the same cluster draws (same sample, same seed), so
differences between dictionaries are paired. Only aggregates are produced; no bio, no user keys.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from rentfriends import dataset_h1 as d1
from rentfriends import h1_tagval as tv

BLOCKS = ("age", "interests", "lifestyle")
DEFINITIONS = ("first", "last", "mean")
Draws = dict[tuple[str, str], np.ndarray]


# --- block increments from log-likelihoods ------------------------------------------------
def increment_draws(ll: pd.DataFrame | pd.Series) -> Draws:
    """Block gains (first / last / mean over the 6 orderings) for each row of model log-likelihoods.

    `ll` has the 8 model names as columns (rows = bootstrap replicates) or is a single Series.
    Blocks: age, interests, lifestyle and the composite `age+interests` (mean of its two orders).
    """
    frame = ll.to_frame().T if isinstance(ll, pd.Series) else ll
    v = {name: frame[name].to_numpy(dtype=float) for name in frame.columns}

    def pair(a: str, b: str) -> str:
        return "_".join(x for x in BLOCKS if x in (a, b))

    out: Draws = {}
    for b in BLOCKS:
        x, y = (o for o in BLOCKS if o != b)
        first = v[b] - v["controls"]
        last = v["full"] - v[pair(x, y)]
        mid_x = v[pair(b, x)] - v[x]
        mid_y = v[pair(b, y)] - v[y]
        out[(b, "first")], out[(b, "last")] = first, last
        out[(b, "mean")] = (2 * first + 2 * last + mid_x + mid_y) / 6
    first = v["age_interests"] - v["controls"]
    last = v["full"] - v["lifestyle"]
    out[("age+interests", "first")], out[("age+interests", "last")] = first, last
    out[("age+interests", "mean")] = (first + last) / 2
    return {(f"dll: {b}", d): arr for (b, d), arr in out.items()}


def quantity_draws(draws: Draws) -> Draws:
    """Add the contrasts, the lifestyle/interests ratio and the block shares to block gains."""
    out = dict(draws)
    for d in DEFINITIONS:
        life = draws[("dll: lifestyle", d)]
        for other in ("age+interests", "interests", "age"):
            out[(f"diff: lifestyle - {other}", d)] = life - draws[(f"dll: {other}", d)]
        out[("ratio: lifestyle / interests", d)] = life / draws[("dll: interests", d)]
    total = sum(draws[(f"dll: {b}", "mean")] for b in BLOCKS)
    for b in BLOCKS:
        out[(f"share: {b}", "mean")] = draws[(f"dll: {b}", "mean")] / total
    return out


def summarise_quantities(obs: Draws, boot: Draws, level: float = 0.95) -> pd.DataFrame:
    """Observed value and percentile CI of every quantity (`obs` arrays have length 1)."""
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for (quantity, definition), reps in boot.items():
        reps = np.asarray(reps, dtype=float)
        rows.append(
            {
                "quantity": quantity,
                "definition": definition,
                "estimate": float(obs[(quantity, definition)][0]),
                "ci_low": float(np.quantile(reps, lo_q)),
                "ci_high": float(np.quantile(reps, hi_q)),
                "boot_se": float(reps.std(ddof=1)),
                "share_positive": float((reps > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def summarise_change(
    obs_a: Draws, boot_a: Draws, obs_b: Draws, boot_b: Draws, level: float = 0.95
) -> pd.DataFrame:
    """Change `b - a` of every quantity; replicates are paired (same cluster draws)."""
    return summarise_quantities(
        {k: obs_b[k] - obs_a[k] for k in obs_a},
        {k: np.asarray(boot_b[k]) - np.asarray(boot_a[k]) for k in boot_a},
        level,
    )


def conservative_ci(by_sender: pd.DataFrame, by_receiver: pd.DataFrame) -> pd.DataFrame:
    """Merge sender- and receiver-clustered summaries; the wider CI is the conservative one."""
    keys = ["quantity", "definition"]
    s, r = by_sender.set_index(keys), by_receiver.set_index(keys)
    out = pd.DataFrame(index=s.index)
    out["estimate"] = s["estimate"]
    for tag, tbl in (("sender", s), ("receiver", r)):
        out[f"ci_low_{tag}"], out[f"ci_high_{tag}"] = tbl["ci_low"], tbl["ci_high"]
    receiver_wider = (r["ci_high"] - r["ci_low"]) > (s["ci_high"] - s["ci_low"])
    out["ci_low"] = np.where(receiver_wider, r["ci_low"], s["ci_low"])
    out["ci_high"] = np.where(receiver_wider, r["ci_high"], s["ci_high"])
    out["wider_is"] = np.where(receiver_wider, "receiver", "sender")
    out["excludes_zero"] = (out["ci_low"] > 0) | (out["ci_high"] < 0)
    return out.reset_index()


# --- decomposition of v0 -> v1 into single tag decisions ----------------------------------
@dataclass(frozen=True)
class Shift:
    """One decision moved relative to v0; `kwargs=None` means it is identical to v0."""

    label: str
    kwargs: dict | None
    note: str = ""


def single_category_shifts(
    tags: list[str], agent_category: Mapping[str, str], final_category: Mapping[str, str]
) -> list[Shift]:
    """One shift per tag: its category from the agent's to the final one, everything else v0."""
    out = []
    for tag in tags:
        a, f = agent_category.get(tag), final_category.get(tag)
        note = f"{a} → {f}"
        if a == f:
            out.append(Shift(tag, None, f"{note} (bez różnicy względem v0)"))
        else:
            out.append(Shift(tag, {"category_override": {tag: f}}, note))
    return out


def single_merge_shifts(merge: Mapping[str, str]) -> list[Shift]:
    """One shift per merge pair; D13 keys and D15 groups are re-pointed for that pair only."""
    out = []
    for src, target in merge.items():
        one = {src: target}
        d13, _ = tv.rekey_d13_map(dict(d1.TAG_TO_STRUCTURED_FIELD_MAP), one)
        pairs, _ = tv.remap_polarity_pairs([(set(p), set(n)) for p, n in d1.POLARITY_PAIRS], one)
        out.append(
            Shift(
                f"{src} → {target}",
                {"tag_merge": one, "d13_map": d13, "polarity_pairs": pairs},
                "scalenie",
            )
        )
    return out


def decompose(
    shifts: list[Shift],
    base_metrics: dict,
    base_df: pd.DataFrame,
    mask: pd.Series,
    data_dir: str | Path,
    docs_dir: str | Path,
) -> pd.DataFrame:
    """Refit once per shift; report the change of the block gains relative to v0 (pooled logit)."""
    rows = []
    for sh in shifts:
        row: dict[str, object] = {"shift": sh.label, "note": sh.note}
        if sh.kwargs is None:
            row.update({f"delta_dll_{b}": 0.0 for b in BLOCKS} | {"share_interests_changed": 0.0})
            rows.append(row)
            continue
        df = tv.build_h1_variant(data_dir, docs_dir, **sh.kwargs)
        m = tv.fit_metrics(df)
        shares = tv.changed_shares(base_df, df, mask)
        for b in BLOCKS:
            row[f"delta_dll_{b}"] = m["dll_mean"][b] - base_metrics["dll_mean"][b]
        row["share_interests_changed"] = shares["interests_set"]
        row["share_lifestyle_tags_changed"] = shares["lifestyle_tags"]
        row["share_conflict_changed"] = shares["lifestyle_tag_conflict"]
        row["ratio"] = m["lifestyle_to_interests_ratio"]
        rows.append(row)
    return pd.DataFrame(rows)


# --- figure ---------------------------------------------------------------------------------
def plot_dictionary_sensitivity(table: pd.DataFrame, path: str | Path, note: str = "") -> Path:
    """Ratio of the lifestyle to the interests gain per tag dictionary, with 95% CIs.

    `table` columns: scenario, estimate, ci_low, ci_high (optionally `baseline` = True for v0).
    Colours follow STYLEGUIDE.md: purple primary series, blue for the comparison (v0), gray for
    the reference line.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    purple, blue, gray, hair = "#A247E3", "#234CE0", "#595959", "#D5D2CB"
    plt.rcParams["font.family"] = ["Plus Jakarta Sans", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(9.5, 0.55 * len(table) + 3.0))
    y = np.arange(len(table))[::-1]
    for yi, (_, row) in zip(y, table.iterrows(), strict=True):
        color = blue if row.get("baseline", False) else purple
        ax.errorbar(
            row["estimate"],
            yi,
            xerr=[[row["estimate"] - row["ci_low"]], [row["ci_high"] - row["estimate"]]],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=2,
            capsize=4,
            markersize=8,
        )
        ax.text(
            row["ci_high"] + 0.1,
            yi,
            f"{row['estimate']:.2f}".replace(".", ",")
            + f"  [{row['ci_low']:.2f}; {row['ci_high']:.2f}]".replace(".", ","),
            va="center",
            fontsize=9,
            color=gray,
        )
    ax.axvline(1.0, color=gray, lw=1.2, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(table["scenario"], fontsize=10)
    ax.set_xlim(0, max(table["ci_high"].max() * 1.45, 2))
    ax.set_xlabel(
        "Ile razy styl życia dodaje więcej niż zainteresowania (1 = tyle samo)", fontsize=10
    )
    ax.grid(axis="x", color=hair, lw=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.suptitle(
        "Styl życia czy zainteresowania? Odpowiedź zależy od tego, jak sklasyfikowano tagi",
        x=0.01,
        ha="left",
        fontsize=12,
        fontweight="bold",
    )
    caption = (
        "Każdy punkt: iloraz przyrostu dopasowania modelu dzięki stylowi życia do przyrostu "
        "dzięki zainteresowaniom,\n"
        "z 95% przedziałem ufności (losowanie osób). Zmieniamy tylko to, które tagi liczą się "
        "jako hobby, a które jako styl życia." + (f"\n{note}" if note else "")
    )
    fig.text(0.01, 0.01, caption, fontsize=8.5, color=gray, va="bottom")
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, facecolor="#F4F2EE")
    plt.close(fig)
    return out


# --- pooled out-of-fold levels -------------------------------------------------------------
def cv_levels(oof: pd.DataFrame, n_boot: int = 1000, seed: int = 42, level: float = 0.95):
    """Pooled out-of-fold logloss / AUC / AUC-PR of every model with sender-bootstrap CIs.

    Same resampling scheme as `h1_audit.paired_cv_differences` (senders drawn with replacement,
    conditional on the fitted fold models).
    """
    from rentfriends import h1_audit as ha
    from rentfriends.h1 import model_subsets

    models = list(model_subsets())
    y = oof["y"].to_numpy()
    order = np.argsort(oof["sender"].to_numpy(), kind="stable")
    cuts = np.flatnonzero(np.diff(oof["sender"].to_numpy()[order])) + 1
    groups = np.split(order, cuts)
    pred = {m: oof[m].to_numpy() for m in models}

    def metrics(idx: np.ndarray | slice) -> dict[str, dict[str, float]]:
        return {m: ha._cv_metrics(y[idx], pred[m][idx]) for m in models}

    obs = metrics(slice(None))
    draws = np.random.default_rng(seed).integers(0, len(groups), size=(n_boot, len(groups)))
    boot = [metrics(np.concatenate([groups[i] for i in row])) for row in draws]
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    rows = []
    for m in models:
        for metric in ("logloss", "auc", "auc_pr"):
            reps = np.array([b[m][metric] for b in boot])
            rows.append(
                {
                    "model": m,
                    "metric": metric,
                    "estimate": obs[m][metric],
                    "ci_low": float(np.quantile(reps, lo_q)),
                    "ci_high": float(np.quantile(reps, hi_q)),
                }
            )
    return pd.DataFrame(rows)
