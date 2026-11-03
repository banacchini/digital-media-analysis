"""H3a pipeline steps called from notebooks/H3a.ipynb. Outputs are aggregates only."""

from __future__ import annotations

import json
import math
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, replace
from importlib import metadata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rentfriends.h3a import classify as C
from rentfriends.h3a import data as D
from rentfriends.h3a import figs as F
from rentfriends.h3a import m4 as M4
from rentfriends.h3a import models as M
from rentfriends.h3a import predictive, sim
from rentfriends.h3a.privacy import suppress_small
from rentfriends.h3a.runner import Runner, fingerprint

CARD = {  # M1 card numbers (before Hyderabad filter and versioning)
    "profile_swipes": 95144,
    "right_swipes": 19495,
    "right_share_pct": 20.49,
    "swipers": 1583,
    "users": 2065,
    "swipes_with_bio": 52371,
    "right_pct_with_bio": 21.5,
    "right_pct_without_bio": 19.2,
    "missing_age_band_swipes": 578,
}

SPEC_LABELS = {
    "main": "Główna",
    "S1": "S1: ≥10 swipe'ów, bez skrajnych",
    "S2a": "S2a: tylko prior_version",
    "S2b": "S2b: cechy z bieżącego users",
    "S3": "S3: z Hyderabad",
    "S4": "S4: kompletność bez 2 pól",
    "S5": "S5: bio < 10 znaków = puste",
    "S6": "S6: surowa liczba tagów",
    "S7": "S7: model rozszerzony",
}
GLMM_L2 = ("S1", "S3", "S4", "S7")


@dataclass
class Params:
    run_level: int = 1
    sample_frac: float = 1.0
    sample_by: str = "sender"
    seed: int = 20261102
    margin: float = 0.10
    fit_timeout_min: float = 90.0
    report_dir: str = "reports/h3a"


@dataclass
class Ctx:
    p: Params
    runner: Runner
    saver: F.FigureSaver
    raw: D.RawData | None = None
    t_all: pd.DataFrame | None = None
    main: pd.DataFrame | None = None
    res: dict = field(default_factory=dict)

    @property
    def is_full(self) -> bool:
        return self.p.sample_frac >= 1.0


def setup(p: Params) -> Ctx:
    Path(p.report_dir).mkdir(parents=True, exist_ok=True)
    runner = Runner(p.report_dir, p.fit_timeout_min)
    saver = F.init(p.report_dir)
    ctx = Ctx(p=p, runner=runner, saver=saver)
    rpath = Path(p.report_dir) / "results.json"
    if rpath.exists():
        ctx.res = json.loads(rpath.read_text())
    ctx.res["params"] = p.__dict__
    write_env(p.report_dir)
    return ctx


def persist(ctx: Ctx) -> None:
    ctx.runner.save_json("results.json", ctx.res)


def write_env(report_dir: str) -> None:
    pkgs = [
        "numpy",
        "pandas",
        "scipy",
        "statsmodels",
        "scikit-learn",
        "gpboost",
        "patsy",
        "matplotlib",
        "papermill",
        "pyarrow",
    ]
    lines = [f"python {sys.version.split()[0]}", f"platform {platform.platform()}"]
    for k in pkgs:
        try:
            lines.append(f"{k} {metadata.version(k)}")
        except metadata.PackageNotFoundError:
            lines.append(f"{k} not installed")
    r = shutil.which("Rscript")
    lines.append(f"Rscript {r or 'not found'}")
    (Path(report_dir) / "env.txt").write_text("\n".join(lines) + "\n")


# ============================================================================ data


def prepare(ctx: Ctx) -> pd.DataFrame:
    """Load, build as-of table, apply sampling and filters; flow table, card check, F0."""
    p = ctx.p
    with ctx.runner.step("load_and_asof"):
        ctx.raw = D.load_raw()
        t = D.build_analysis_table(ctx.raw).table
    full = t
    t = D.sample_by_sender(t, p.sample_frac, p.seed)
    no_hyd = t[t["hyderabad"] == 0]
    main = D.complete_case(no_hyd)
    ctx.t_all, ctx.main = t, main

    def row(step, df):
        return {
            "krok": step,
            "swipes": len(df),
            "prawe": int(df["y_right"].sum()),
            "nadawcy": df["s_key"].nunique(),
            "odbiorcy": df["r_key"].nunique(),
        }

    flow = pd.DataFrame(
        [
            row("Swipe'y na profile" + ("" if ctx.is_full else f" (próba {p.sample_frac:.0%})"), t),
            row("Po wykluczeniu Hyderabad (nadawca lub odbiorca)", no_hyd),
            row("Po complete-case (zmienne modelu)", main),
        ]
    )
    ctx.saver.save_table(flow, "h3a_flow")
    miss = no_hyd[D.MODEL_VARS].isna().sum()
    ctx.res["flow"] = flow.to_dict("records")
    ctx.res["missing_by_var_after_hyd"] = {k: int(v) for k, v in miss.items() if v}

    # Card consistency (computed on the full table, before Hyderabad filter).
    hyd = D.hyderabad_users(ctx.raw)
    ours = {
        "profile_swipes": len(full),
        "right_swipes": int(full["y_right"].sum()),
        "right_share_pct": 100 * full["y_right"].mean(),
        "swipers": full["s_key"].nunique(),
        "users": len(ctx.raw.users),
        "swipes_with_bio": int(full["has_bio"].sum()),
        "right_pct_with_bio": 100 * full.loc[full["has_bio"] == 1, "y_right"].mean(),
        "right_pct_without_bio": 100 * full.loc[full["has_bio"] == 0, "y_right"].mean(),
        "missing_age_band_swipes": int(full["age_band_diff"].isna().sum()),
    }
    # Same quantity as on the card: bio from the current users row, not as-of.
    cur_bio = ctx.raw.users.set_index("user_key")["bio"]
    cur_has = 1 - D.v.bio_empty(full["r_key"].map(cur_bio))
    ours_cur = {
        "swipes_with_bio": int(cur_has.sum()),
        "right_pct_with_bio": 100 * full.loc[cur_has.to_numpy() == 1, "y_right"].mean(),
        "right_pct_without_bio": 100 * full.loc[cur_has.to_numpy() == 0, "y_right"].mean(),
    }
    chk = []
    for k, card in CARD.items():
        val = ours[k]
        dev = 100 * (val - card) / card
        chk.append(
            {
                "miara": k,
                "karta": card,
                "asof": round(val, 3),
                "odchylenie_pct": round(dev, 3),
                "bieżący_users": round(ours_cur[k], 3) if k in ours_cur else None,
                "flaga_>1pct": abs(dev) > 1,
            }
        )
    chk = pd.DataFrame(chk)
    ctx.saver.save_table(chk, "h3a_card_check")
    ctx.res["card_check"] = chk.to_dict("records")
    ctx.res["hyderabad"] = {
        "accounts": len(hyd),
        "accounts_any_version": int(
            ctx.raw.history.loc[ctx.raw.history["city"] == D.HYDERABAD, "user_key"].nunique()
        ),
        "profile_swipes_removed": int(full["hyderabad"].sum()),
        "as_sender": int(full["s_key"].isin(hyd).sum()),
        "as_receiver": int(full["r_key"].isin(hyd).sum()),
    }
    ctx.res["asof_source_counts"] = {
        side: full[f"{side}_asof_source"].value_counts().to_dict() for side in ("s", "r")
    } | {"pair": full["asof_source"].value_counts().to_dict()}
    # G18: provider bio_length vs text length (share of receiver snapshots seen in swipes)
    snaps = full.drop_duplicates(["r_key", "r_version"])
    ctx.res["g18_bio_length_mismatch"] = {
        "receiver_snapshots": len(snaps),
        "share_mismatch": float(snaps["r_bio_length_mismatch"].mean()),
        "share_swipes_mismatch": float(full["r_bio_length_mismatch"].mean()),
    }

    # F0
    fig, ax = plt.subplots()
    labels = ["Swipe'y na profile", "Bez Hyderabad", "Complete-case"]
    vals = flow["swipes"].to_numpy()
    ax.barh(labels[::-1], vals[::-1], color=F.BLUE, height=0.55)
    for i, val in enumerate(vals[::-1]):
        ax.text(val, i, f" {val:,}".replace(",", " "), va="center", fontsize=14)
    ax.set_xlabel("Liczba swipe'ów na profile")
    ax.set_title("Przepływ próby H3a")
    ax.set_xlim(0, vals.max() * 1.18)
    ax.grid(axis="y", visible=False)
    ctx.saver.save_fig(
        fig,
        "h3a_00_przeplyw_proby",
        flow,
        caption="Rys. F0. Przepływ próby: swipe'y na profile, po wykluczeniu kont "
        "Hyderabad i po complete-case na zmiennych modelu.",
        model="dane",
        n_swipes=len(main),
        n_receivers=main["r_key"].nunique(),
    )
    plt.show()
    persist(ctx)
    return flow


# ============================================================================ descriptives


def _boot_rate_by_receiver(df: pd.DataFrame, n_boot: int, seed: int) -> tuple[float, float]:
    r = pd.factorize(df["r_key"])[0]
    G = r.max() + 1
    ys = np.bincount(r, weights=df["y_right"].to_numpy(float), minlength=G)
    ns = np.bincount(r, minlength=G).astype(float)
    rng = np.random.default_rng(seed)
    rates = np.empty(n_boot)
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, G, G), minlength=G)
        rates[b] = (w @ ys) / (w @ ns)
    return tuple(np.percentile(rates, [2.5, 97.5]))


def describe(ctx: Ctx) -> None:
    """Descriptive table, F1 (raw rates), F2 (bio length), F8 (balance)."""
    t = ctx.main
    with ctx.runner.step("descriptives"):
        rows = []
        for (sx, hb), g in t.groupby(["sender_sex", "has_bio"]):
            lo, hi = _boot_rate_by_receiver(g, 1000, ctx.p.seed)
            rows.append(
                {
                    "plec_nadawcy": sx,
                    "has_bio": int(hb),
                    "swipes": len(g),
                    "n_receivers": g["r_key"].nunique(),
                    "n_senders": g["s_key"].nunique(),
                    "right_rate": g["y_right"].mean(),
                    "lo95": lo,
                    "hi95": hi,
                }
            )
        f1 = pd.DataFrame(rows)
        f1["n_users_min"] = f1[["n_receivers", "n_senders"]].min(axis=1)
        f1 = suppress_small(
            f1, "n_users_min", ["right_rate", "lo95", "hi95", "swipes", "n_receivers", "n_senders"]
        )
        ctx.saver.save_table(f1, "h3a_desc_rates_by_bio_sex")

        fig, ax = plt.subplots()
        sexes = ["F", "M", "O"]
        for k, hb in enumerate((0, 1)):
            sub = f1[f1["has_bio"] == hb].set_index("plec_nadawcy").reindex(sexes)
            x = np.arange(3) + (k - 0.5) * 0.25
            col = F.GRAY if hb == 0 else F.BLUE
            ax.errorbar(
                x,
                100 * sub["right_rate"],
                yerr=[
                    100 * (sub["right_rate"] - sub["lo95"]),
                    100 * (sub["hi95"] - sub["right_rate"]),
                ],
                fmt="o",
                ms=9,
                capsize=5,
                color=col,
                lw=2,
                label="z bio" if hb else "bez bio",
            )
        ax.set_xticks(range(3), ["Kobiety (F)", "Mężczyźni (M)", "Inna (O)"])
        ax.set_xlabel("Płeć nadawcy")
        ax.set_ylabel("Odsetek prawych swipe'ów [%]")
        ax.set_title("Prawe swipe'y wg bio odbiorcy (surowo, bez kontroli)")
        ax.legend(loc="upper left")
        ctx.saver.save_fig(
            fig,
            "h3a_01_odsetek_prawych_bio_plec",
            f1,
            caption="Rys. F1. Odsetek prawych swipe'ów wg obecności bio odbiorcy i "
            "płci nadawcy; 95% CI z bootstrapu po odbiorcach (B = 1000). "
            "Opisowo, bez kontroli.",
            model="opisowe",
            n_swipes=len(t),
            n_receivers=t["r_key"].nunique(),
        )
        plt.show()

        # F2: bio length among non-empty (swipe level = exposures)
        ne = t[t["has_bio"] == 1]
        bins = np.arange(0, 260, 10)
        ne_bin = pd.cut(ne["bio_len"], bins=bins, right=False, include_lowest=True)
        h = ne.groupby(ne_bin, observed=False).agg(
            swipes=("y_right", "size"), n_receivers=("r_key", "nunique")
        )
        h = h.reset_index().rename(columns={"bio_len": "bin"})
        h["bin_left"] = bins[:-1]
        h["bin"] = h["bin"].astype(str)
        h = suppress_small(h, "n_receivers", ["swipes"])
        share_empty = 1 - t["has_bio"].mean()
        rec_empty = 1 - t.drop_duplicates("r_key", keep="last")["has_bio"].mean()
        fig, ax = plt.subplots()
        ax.bar(h["bin_left"] + 5, h["swipes"], width=9, color=F.BLUE)
        ax.axvline(250, color=F.VERMILION, lw=2, ls="--")
        ax.text(
            247,
            ax.get_ylim()[1] * 0.92,
            "sufit pola: 250",
            ha="right",
            color=F.VERMILION,
            fontsize=14,
        )
        ax.set_xlabel("Długość bio [znaki, po strip()]")
        ax.set_ylabel("Liczba swipe'ów (ekspozycji)")
        ax.set_title(f"Długość niepustych bio; puste: {share_empty:.1%} swipe'ów")
        ctx.saver.save_fig(
            fig,
            "h3a_02_dlugosc_bio",
            h.assign(share_empty_swipes=share_empty, share_empty_receivers_last=rec_empty),
            caption="Rys. F2. Rozkład długości niepustych bio odbiorców na poziomie "
            "swipe'ów (wersja as-of); linia: sufit pola 250 znaków. Kosze "
            "z < 5 odbiorcami wytłumione.",
            model="opisowe",
            n_swipes=len(ne),
            n_receivers=ne["r_key"].nunique(),
        )
        plt.show()
        ctx.res["desc"] = {
            "share_empty_swipes": share_empty,
            "share_cap_among_nonempty": float(ne["bio_len_cap"].mean()),
            "bio_len_median_nonempty": float(ne["bio_len"].median()),
            "bio_len_iqr_nonempty": [float(ne["bio_len"].quantile(q)) for q in (0.25, 0.75)],
        }

        # F8: balance of controls (standardised mean differences, swipe level)
        bal_vars = [
            "profile_completeness",
            "profile_completeness_alt",
            "tag_count_receiver",
            "tag_zero",
            "tag_cap",
            "age_band_diff",
            "same_band",
        ]
        dm = pd.get_dummies(t[["sex_pair", "same_city"]], dtype=float)
        B = pd.concat([t[bal_vars].astype(float), dm], axis=1)
        a, b = B[t["has_bio"] == 1], B[t["has_bio"] == 0]
        smd = (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
        f8 = pd.DataFrame(
            {
                "zmienna": smd.index,
                "smd": smd.to_numpy(),
                "mean_has_bio1": a.mean().to_numpy(),
                "mean_has_bio0": b.mean().to_numpy(),
            }
        )
        f8 = f8.sort_values("smd")
        ctx.saver.save_table(f8, "h3a_balance_smd")
        fig, ax = plt.subplots(figsize=(10, 5.6))
        ax.axvspan(-0.1, 0.1, color=F.LIGHT, alpha=0.6, lw=0)
        ax.axvline(0, color=F.GRAY, lw=1)
        ax.plot(f8["smd"], range(len(f8)), "o", color=F.BLUE, ms=8)
        ax.set_yticks(range(len(f8)), f8["zmienna"], fontsize=11)
        ax.set_xlabel("Standaryzowana różnica średnich (z bio − bez bio)")
        ax.set_title("Balans kontroli wg bio odbiorcy")
        ax.grid(axis="y", visible=False)
        F.pl_decimal(ax, "x")
        ctx.saver.save_fig(
            fig,
            "h3a_08_balans_kontroli",
            f8,
            caption="Rys. F8. Standaryzowane różnice średnich zmiennych kontrolnych "
            "między swipe'ami na profile z bio i bez bio; pas: |SMD| ≤ 0,1.",
            model="opisowe",
            n_swipes=len(t),
            n_receivers=t["r_key"].nunique(),
        )
        plt.show()
    persist(ctx)


# ============================================================================ model helpers


def _arrays(df: pd.DataFrame, spec: M.Spec):
    X, meta = M.build_design(df, spec)
    names = list(X.columns)
    return (
        X.to_numpy(float),
        df["y_right"].to_numpy(float),
        M.codes(df["s_key"]),
        M.codes(df["r_key"]),
        names,
        meta,
    )


def _spec_fp(spec: M.Spec) -> dict:
    """Spec as a dict for the cache fingerprint; level-3 fields are omitted at their defaults,
    so fits cached at levels 1-2 stay valid."""
    d = dict(spec.__dict__)
    if d.get("control_set") == "full":
        d.pop("control_set")
    if not d.get("interact_cols"):
        d.pop("interact_cols", None)
    return d


def fit_models(
    ctx: Ctx, key: str, df: pd.DataFrame, spec: M.Spec, which: tuple[str, ...] = ("M1", "M2", "M3")
) -> dict:
    X, y, s, r, names, meta = _arrays(df, spec)
    fp = fingerprint(X, y, s, r, extra={"spec": _spec_fp(spec), "names": names})
    out = ctx.res.setdefault("fits", {}).setdefault(key, {})
    out["n_obs"] = len(y)
    out["n_senders"] = int(s.max() + 1)
    out["n_receivers"] = int(r.max() + 1)
    out["dropped_constant"] = meta["dropped_constant"]
    out["dropped_separated"] = meta.get("dropped_separated", [])
    out["dropped_collinear"] = meta.get("dropped_collinear", [])
    bio = (
        "has_bio"
        if spec.bio_terms == "binary" and not spec.drop_bio and not spec.interact_cols
        else None
    )
    if "M1" in which:
        out["M1"] = ctx.runner.fit(f"{key}__M1", M.fit_glmm, X, y, s, r, names, fp=fp)
    if "M2" in which:
        out["M2"] = ctx.runner.fit(
            f"{key}__M2", M.fit_pooled_logit, X, y, s, r, names, bio, fp=fp, timeout=False
        )
    if "M3" in which:
        spec3 = replace(spec, fe_sender=True)
        X3, _, _, _, names3, meta3 = _arrays(df, spec3)
        fp3 = fingerprint(X3, y, s, r, extra={"spec": _spec_fp(spec3), "names": names3})
        out["M3"] = ctx.runner.fit(
            f"{key}__M3", M.fit_fe_logit, X3, y, s, r, names3, fp=fp3, timeout=False
        )
        out["M3"]["dropped_separated_design"] = meta3.get("dropped_separated", [])
    persist(ctx)
    return out


def bio_row(key: str, model: str, res: dict, margin: float, coef: str = "has_bio") -> dict:
    b, se = M.coef_of(res, coef)
    row = {"spec": key, "model": model, "status": (res or {}).get("status", "not_run")}
    if math.isfinite(b) and math.isfinite(se):
        row |= C.wald_ci(b, se)
        row["label"] = C.classify(b, se, margin)
        row["mde_or"] = C.mde_or(se)
    else:
        row["label"] = C.NOT_ESTIMATED
    return row


# ============================================================================ sanity check


def sanity_check(ctx: Ctx) -> dict:
    """GLMM on simulated y (real design, known parameters): bias and 95% coverage."""
    n_reps = 20 if ctx.is_full else 3
    X, _, s, r, names, _ = _arrays(ctx.main, M.Spec())
    reps = []
    with ctx.runner.step("sanity_glmm_sim"):
        for i in range(n_reps):
            fp = fingerprint(X, s, r, extra={"rep": i, "seed": ctx.p.seed})
            reps.append(
                ctx.runner.fit(
                    f"sim__rep{i:02d}", sim.sim_rep, X, names, s, r, ctx.p.seed + i, fp=fp
                )
            )
    summ = sim.summarise(reps)
    ctx.res["sanity"] = summ
    persist(ctx)
    return summ


# ============================================================================ main models


def main_models(ctx: Ctx) -> pd.DataFrame:
    with ctx.runner.step("main_models"):
        out = fit_models(ctx, "main", ctx.main, M.Spec())
    rows = [bio_row("main", m, out.get(m), ctx.p.margin) for m in ("M1", "M2", "M3")]
    tab = pd.DataFrame(rows)
    lab1 = tab.loc[tab.model == "M1", "label"].iloc[0]
    lab2 = tab.loc[tab.model == "M2", "label"].iloc[0]
    if out["M1"].get("status") != "ok":
        # Fallback (prompt §6): M2 becomes the main model, no claim about popularity control.
        final = f"{lab2} (fallback: M2 jako model główny, bez kontroli popularności)"
    else:
        final = C.final_label(lab1, lab2, None)
    ame = out["M2"].get("ame", {})
    ctx.res["verdict"] = {
        "label_M1": lab1,
        "label_M2": lab2,
        "label_M3": tab.loc[tab.model == "M3", "label"].iloc[0],
        "final": final,
        "lme4": "pominięty (brak Rscript)" if not shutil.which("Rscript") else "nie uruchomiony",
        "ame_M2": ame,
    }
    m1 = out["M1"]
    ctx.res["m1_diag"] = {
        k: m1.get(k)
        for k in (
            "status",
            "optimizer",
            "convergence_status",
            "n_iter",
            "time_s",
            "var_sender",
            "var_receiver",
            "var_sender_se",
            "var_receiver_se",
            "loglik",
            "attempts",
        )
    }
    ctx.res["m3_diag"] = {
        k: out["M3"].get(k)
        for k in (
            "n_obs_used",
            "n_senders_used",
            "n_senders_dropped_all_same",
            "dropped_cols_no_within_var",
        )
    }
    tab_out = tab[
        [
            "model",
            "status",
            "beta",
            "se",
            "or",
            "or_lo95",
            "or_hi95",
            "or_lo90",
            "or_hi90",
            "p",
            "mde_or",
            "label",
        ]
    ]
    ctx.saver.save_table(tab_out, "h3a_main_result")
    # Full coefficient table (all covariates), M1 and M2
    coefs = []
    for m in ("M1", "M2", "M3"):
        r = out.get(m) or {}
        for nm, b, se in zip(r.get("names", []), r.get("coef", []), r.get("se", []), strict=False):
            coefs.append({"model": m, "term": nm, "beta": b, "se": se})
    ctx.saver.save_table(pd.DataFrame(coefs), "h3a_main_all_coefficients")
    ctx.res["main_table"] = tab_out.to_dict("records")
    persist(ctx)
    return tab_out


# ============================================================================ M5


def m5_length(ctx: Ctx) -> pd.DataFrame:
    sub = ctx.main[ctx.main["has_bio"] == 1]
    with ctx.runner.step("M5_length"):
        lin = fit_models(
            ctx, "M5_log", sub, M.Spec(name="M5_log", bio_terms="log_len"), which=("M1", "M2")
        )
        spl = fit_models(
            ctx, "M5_spline", sub, M.Spec(name="M5_spline", bio_terms="spline"), which=("M2",)
        )
    rows = []
    for m in ("M1", "M2"):
        b, se = M.coef_of(lin[m], "log1p_bio_len")
        if math.isfinite(b):
            ln2 = math.log(2)
            rows.append(
                {
                    "model": m,
                    "beta_log1p_len": b,
                    "se": se,
                    "or_doubling": math.exp(b * ln2),
                    "or_doubling_lo95": math.exp((b - C.Z95 * se) * ln2),
                    "or_doubling_hi95": math.exp((b + C.Z95 * se) * ln2),
                    "status": lin[m].get("status"),
                }
            )
        bc, sec = M.coef_of(lin[m], "bio_len_cap")
        if rows and math.isfinite(bc):
            rows[-1] |= {
                "or_cap": math.exp(bc),
                "or_cap_lo95": math.exp(bc - C.Z95 * sec),
                "or_cap_hi95": math.exp(bc + C.Z95 * sec),
            }
    tab = pd.DataFrame(rows)
    ctx.saver.save_table(tab, "h3a_m5_length")
    ctx.res["m5"] = tab.to_dict("records")

    # Dose-response curve from the M2 spline fit (full covariance available).
    r2 = spl["M2"]
    names = r2["names"]
    idx = [names.index(n) for n in names if n.startswith("bio_spline_")]
    beta = np.array(r2["coef"])[idx]
    V = np.array(r2["cov"])[np.ix_(idx, idx)]
    _, di = M.spline_basis(np.log1p(sub["bio_len"].to_numpy(float)))
    grid = np.arange(1, 250)
    ref = float(sub["bio_len"].median())
    Bg, _ = M.spline_basis(np.log1p(grid.astype(float)), design_info=di)
    Br, _ = M.spline_basis(np.log1p(np.array([ref])), design_info=di)
    Dm = Bg - Br
    eta = Dm @ beta
    se = np.sqrt(np.einsum("ij,jk,ik->i", Dm, V, Dm))
    curve = pd.DataFrame(
        {
            "bio_len": grid,
            "or_vs_median": np.exp(eta),
            "lo95": np.exp(eta - C.Z95 * se),
            "hi95": np.exp(eta + C.Z95 * se),
        }
    )
    # suppress support: lengths with < 5 distinct receivers in the data get NaN
    nrec = sub.groupby("bio_len")["r_key"].nunique().reindex(grid, fill_value=0).to_numpy()
    curve["n_receivers_at_len"] = nrec
    curve["n_receivers_ge_len_window"] = (
        pd.Series(nrec).rolling(11, center=True, min_periods=1).sum().to_numpy()
    )
    curve = curve.drop(columns=["n_receivers_at_len"])
    curve = suppress_small(curve, "n_receivers_ge_len_window", ["or_vs_median", "lo95", "hi95"])
    fig, ax = plt.subplots()
    ax.fill_between(
        curve["bio_len"],
        curve["lo95"],
        curve["hi95"],
        color=F.BLUE,
        alpha=0.2,
        lw=0,
        label="95% CI",
    )
    ax.plot(
        curve["bio_len"], curve["or_vs_median"], color=F.BLUE, lw=2.5, label="OR względem mediany"
    )
    ax.axhline(1, color=F.GRAY, lw=1)
    ax.axvline(250, color=F.VERMILION, lw=2, ls="--")
    ax.text(246, ax.get_ylim()[1] * 0.97, "sufit 250", ha="right", va="top", color=F.VERMILION)
    ax.set_xscale("log")
    ax.set_xticks([1, 3, 10, 30, 100, 250], ["1", "3", "10", "30", "100", "250"])
    ax.set_xlabel("Długość bio [znaki, skala log]")
    ax.set_ylabel(f"OR prawego swipe'a vs {ref:.0f} znaków")
    ax.set_title("Długość bio a prawy swipe (M2, spline, tylko niepuste bio)")
    ax.legend(loc="lower right")
    F.pl_decimal(ax, "y")
    ctx.saver.save_fig(
        fig,
        "h3a_05_dose_response_dlugosc",
        curve,
        caption="Rys. F5. Krzywa dose-response długości bio (naturalny spline 3 df "
        "na log1p(długość), pooled logit z klastrowaniem dwukierunkowym, "
        "kontrole jak w M1), tylko niepuste bio. Opisowo, bez werdyktu.",
        model="M5 (M2 spline)",
        n_swipes=len(sub),
        n_receivers=sub["r_key"].nunique(),
    )
    plt.show()
    persist(ctx)
    return tab


# ============================================================================ M6


def m6_predictive(ctx: Ctx) -> dict:
    t = ctx.main
    with ctx.runner.step("M6_predictive"):
        Xb, y, s, r, nb, _ = _arrays(t, M.Spec(drop_bio=True))
        Xf, _, _, _, nf, _ = _arrays(t, M.Spec())
        fp = fingerprint(Xb, Xf, y, s, extra={"seed": ctx.p.seed})
        res = ctx.runner.fit(
            "M6_predictive",
            predictive.predictive_increment,
            Xb,
            Xf,
            y,
            s,
            5,
            1000,
            ctx.p.seed,
            fp=fp,
            timeout=False,
        )
    ctx.res["m6"] = res
    tab = pd.DataFrame(
        [
            {
                "miara": "ΔlogLoss (pełny − baseline)",
                "wartosc": res["d_logloss"],
                "lo95": res["d_logloss_lo95"],
                "hi95": res["d_logloss_hi95"],
            },
            {
                "miara": "ΔAUC (pełny − baseline)",
                "wartosc": res["d_auc"],
                "lo95": res["d_auc_lo95"],
                "hi95": res["d_auc_hi95"],
            },
        ]
    )
    ctx.saver.save_table(tab, "h3a_m6_predictive")
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.6))
    for ax, (_, row), col in zip(axes, tab.iterrows(), (F.BLUE, F.GREEN), strict=True):
        ax.errorbar(
            [0],
            [row["wartosc"]],
            yerr=[[row["wartosc"] - row["lo95"]], [row["hi95"] - row["wartosc"]]],
            fmt="o",
            ms=10,
            capsize=8,
            color=col,
            lw=2.5,
        )
        ax.axhline(0, color=F.GRAY, lw=1)
        ax.set_xticks([])
        ax.set_xlim(-1, 1)
        ax.set_title(row["miara"].split(" (")[0])
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-3, 3))
    axes[0].set_ylabel("Różnica (5-krotna CV po nadawcach)")
    fig.suptitle(
        "Przyrost predykcyjny po dodaniu has_bio (opisowo)", fontsize=17, fontweight="bold"
    )
    fig.tight_layout()
    ctx.saver.save_fig(
        fig,
        "h3a_07_przyrost_predykcyjny",
        tab,
        caption="Rys. F7. Zmiana log loss (ujemna = lepiej) i AUC po dodaniu has_bio "
        "do pooled logitu; predykcje out-of-fold (GroupKFold po nadawcach, "
        "5 foldów), 95% CI z bootstrapu po nadawcach (B = 1000). Opisowe.",
        model="M6",
        n_swipes=len(t),
        n_receivers=t["r_key"].nunique(),
    )
    plt.show()
    persist(ctx)
    return res


# ============================================================================ M4


def m4_within(ctx: Ctx) -> dict:
    """Gate funnel computed on the full data (cheap) and, if passed, the within estimates."""
    with ctx.runner.step("M4_within"):
        full_main = D.complete_case(ctx.t_all[ctx.t_all["hyderabad"] == 0])
        if not ctx.is_full:  # funnel must come from the full data (prompt §12.4)
            t = D.build_analysis_table(ctx.raw).table
            full_main = D.complete_case(t[t["hyderabad"] == 0])
        fun, s = M4.funnel_and_sample(full_main, ctx.raw.history)
        fun_c, s_c = M4.funnel_and_sample(full_main, ctx.raw.history, clean_only=True)
        res = {"funnel": fun, "funnel_clean": fun_c}
        if fun["gate_passed"]:
            res["lpm"] = M4.estimate_lpm(s)
            try:
                res["fe_logit"] = M4.estimate_fe_logit(s)
            except Exception as e:  # noqa: BLE001
                res["fe_logit"] = {"status": "failed", "error": repr(e)}
            if fun_c["gate_passed"]:
                res["lpm_clean"] = M4.estimate_lpm(s_c)
        else:
            res["verdict"] = (
                "niemożliwe do zmierzenia tym projektem: "
                f"{fun['with_min_swipes_each_side']} odbiorców < {fun['gate_threshold']}"
            )
    steps = pd.DataFrame(
        [
            {"etap": "Odbiorcy w próbie głównej", "odbiorcy": fun["receivers_in_sample"]},
            {"etap": "…ze zmianą tekstu bio", "odbiorcy": fun["with_bio_text_change"]},
            {"etap": "…ze zmianą pusty↔niepusty", "odbiorcy": fun["with_status_change"]},
            {
                "etap": "…z ≥5 swipe'ami po każdej stronie",
                "odbiorcy": fun["with_min_swipes_each_side"],
            },
        ]
    )
    steps["odbiorcy_wariant_czysty"] = [
        fun_c["receivers_in_sample"],
        fun_c["with_bio_text_change"],
        fun_c["with_status_change"],
        fun_c["with_min_swipes_each_side"],
    ]
    steps_pub = suppress_small(steps.assign(n=steps["odbiorcy"]), "n", ["odbiorcy"]).drop(
        columns="n"
    )
    steps_pub["odbiorcy_wariant_czysty"] = steps["odbiorcy_wariant_czysty"].where(
        steps["odbiorcy_wariant_czysty"] >= 5
    )
    ctx.saver.save_table(steps_pub, "h3a_m4_gate_funnel")
    fig, ax = plt.subplots()
    ax.barh(steps["etap"][::-1], steps["odbiorcy"][::-1], color=F.BLUE, height=0.55)
    for i, val in enumerate(steps["odbiorcy"][::-1]):
        ax.text(val, i, f" {val}", va="center")
    ax.axvline(M4.GATE_MIN_RECEIVERS, color=F.VERMILION, lw=2, ls="--")
    ax.text(
        M4.GATE_MIN_RECEIVERS,
        -0.6,
        f" próg bramki: {M4.GATE_MIN_RECEIVERS}",
        color=F.VERMILION,
        va="center",
    )
    ax.set_xscale("log")
    ax.set_xlabel("Liczba odbiorców [skala log]")
    passed = "przechodzi" if fun["gate_passed"] else "nie przechodzi"
    ax.set_title(f"M4: bramka wykonalności analizy w obrębie odbiorcy ({passed})")
    ax.grid(axis="y", visible=False)
    ctx.saver.save_fig(
        fig,
        "h3a_06_bramka_m4",
        steps_pub,
        caption="Rys. F6. Lejek bramki wykonalności M4 (pełne dane, po wykluczeniu "
        "swipe'ów z dnia zmiany statusu bio i przypisanych do first_version).",
        model="M4",
        n_swipes=fun["swipes_after_exclusions"],
        n_receivers=fun["with_min_swipes_each_side"],
    )
    plt.show()
    ctx.res["m4"] = res
    persist(ctx)
    return res


# ============================================================================ sensitivity


def sensitivity_samples(ctx: Ctx) -> dict[str, tuple[pd.DataFrame, M.Spec]]:
    t, main = ctx.t_all, ctx.main
    n = main.groupby("s_key")["y_right"].agg(["size", "mean"])
    ok_senders = n[(n["size"] >= 10) & (n["mean"] > 0) & (n["mean"] < 1)].index
    ctx.res["s1_counts"] = {
        "senders_main": int(len(n)),
        "senders_ge10": int((n["size"] >= 10).sum()),
        "all_right_ge10": int(((n["size"] >= 10) & (n["mean"] == 1)).sum()),
        "all_left_ge10": int(((n["size"] >= 10) & (n["mean"] == 0)).sum()),
        "senders_kept": int(len(ok_senders)),
    }
    t_cur = D.build_analysis_table(ctx.raw, use_current_users=True).table
    t_cur = t_cur[t_cur["s_key"].isin(set(t["s_key"]))]
    out = {
        "S1": (main[main["s_key"].isin(set(ok_senders))], M.Spec(name="S1")),
        "S2a": (main[main["asof_source"] == "prior_version"], M.Spec(name="S2a")),
        "S2b": (D.complete_case(t_cur[t_cur["hyderabad"] == 0]), M.Spec(name="S2b")),
        "S3": (D.complete_case(t), M.Spec(name="S3")),
        "S4": (main, M.Spec(name="S4", completeness_var="profile_completeness_alt")),
        "S5": (main, M.Spec(name="S5", bio_var="has_bio_alt10")),
        "S6": (main, M.Spec(name="S6", tag_vars=("tag_count_raw", "tag_zero_raw", "tag_cap_raw"))),
        "S7": (main, M.Spec(name="S7", extended=True)),
    }
    return out


def sensitivity(ctx: Ctx, level: int) -> pd.DataFrame:
    samples = sensitivity_samples(ctx)
    rows = []
    with ctx.runner.step(f"sensitivity_level{level}"):
        for key, (df, spec) in samples.items():
            which = ("M2", "M3") + (("M1",) if level >= 2 and key in GLMM_L2 else ())
            out = fit_models(ctx, key, df, spec, which=which)
            for m in ("M1", "M2", "M3"):
                if m in out:
                    r = bio_row(key, m, out[m], ctx.p.margin)
                    r |= {"n_obs": out["n_obs"], "n_receivers": out["n_receivers"]}
                    rows.append(r)
        s8 = sensitivity_s8(ctx)
    tab = pd.DataFrame(rows)
    cols = [
        "spec",
        "model",
        "status",
        "n_obs",
        "n_receivers",
        "beta",
        "se",
        "or",
        "or_lo95",
        "or_hi95",
        "or_lo90",
        "or_hi90",
        "p",
        "label",
    ]
    tab = tab[[c for c in cols if c in tab.columns]]
    ctx.saver.save_table(tab, "h3a_sensitivity")
    ctx.res["sensitivity_table"] = tab.to_dict("records")
    ctx.res["s8"] = s8
    persist(ctx)
    return tab


def sensitivity_s8(ctx: Ctx) -> dict:
    main = ctx.main
    strata = {}
    for sx in ("F", "M", "O"):
        df = main[main["sender_sex"] == sx]
        n_s, n_right = df["s_key"].nunique(), int(df["y_right"].sum())
        if sx == "O" and (n_s < 30 or n_right < 100):
            strata[sx] = {"skipped": f"za mało danych: {n_s} nadawców, {n_right} prawych"}
            continue
        out = fit_models(ctx, f"S8_{sx}", df, M.Spec(name=f"S8_{sx}"), which=("M2", "M3"))
        strata[sx] = {m: bio_row(f"S8_{sx}", m, out[m], ctx.p.margin) for m in ("M2", "M3")}
        strata[sx]["n_senders"] = n_s
    # interaction test (pooled logit, two-way clustered Wald test)
    out = fit_models(
        ctx,
        "S8_interaction",
        main,
        M.Spec(name="S8_int", interaction_sender_sex=True),
        which=("M2",),
    )
    r = out["M2"]
    idx = [i for i, n in enumerate(r["names"]) if n.startswith("has_bio:sender_sex=")]
    b = np.array(r["coef"])[idx]
    V = np.array(r["cov"])[np.ix_(idx, idx)]
    from scipy.stats import chi2

    w = float(b @ np.linalg.solve(V, b)) if idx else float("nan")
    inter = {
        "terms": [r["names"][i] for i in idx],
        "coef": b.tolist(),
        "se": np.sqrt(np.diag(V)).tolist(),
        "wald_chi2": w,
        "df": len(idx),
        "p": float(chi2.sf(w, len(idx))) if idx else float("nan"),
    }
    res = {"strata": strata, "interaction": inter}
    # F4
    rows = []
    for sx, d in strata.items():
        for m in ("M2", "M3"):
            if m in d and "or" in d[m]:
                rows.append(
                    {
                        "plec_nadawcy": sx,
                        "model": m,
                        **{
                            k: d[m][k]
                            for k in ("or", "or_lo95", "or_hi95", "or_lo90", "or_hi90", "label")
                        },
                    }
                )
    f4 = pd.DataFrame(rows)
    fig, ax = plt.subplots()
    _margin_band(ax, ctx.p.margin)
    ylabels = []
    for i, (_, row) in enumerate(f4.iterrows()):
        col = F.BLUE if row["model"] == "M2" else F.GREEN
        _ci(ax, i, row, col)
        ylabels.append(f"{row['plec_nadawcy']} · {row['model']}")
    ax.set_yticks(range(len(f4)), ylabels)
    ax.invert_yaxis()
    ax.set_xscale("log")
    _or_ticks(ax)
    ax.set_xlabel("OR prawego swipe'a: bio vs brak bio")
    ax.set_title(f"Stratyfikacja po płci nadawcy (interakcja: p = {inter['p']:.3f})")
    ax.grid(axis="y", visible=False)
    ctx.saver.save_fig(
        fig,
        "h3a_04_stratyfikacja_plec",
        f4.assign(
            interaction_wald_chi2=inter["wald_chi2"],
            interaction_df=inter["df"],
            interaction_p=inter["p"],
        ),
        caption="Rys. F4. OR dla has_bio w warstwach płci nadawcy (M2: pooled logit, klastrowanie "
        "dwukierunkowe; M3: FE nadawcy) z 95% (cienka) i 90% (gruba) CI; test Walda "
        "interakcji has_bio × płeć nadawcy w pooled logit.",
        model="S8",
        n_swipes=len(main),
        n_receivers=main["r_key"].nunique(),
    )
    plt.show()
    return res


# ============================================================================ forest plot


def _margin_band(ax, margin):
    ax.axvspan(
        math.exp(-margin), math.exp(margin), color=F.LIGHT, alpha=0.6, lw=0, label="praktyczne zero"
    )
    ax.axvline(1, color=F.GRAY, lw=1.2)


def _ci(ax, y, row, col, label=None):
    ax.hlines(y, row["or_lo95"], row["or_hi95"], color=col, lw=1.6)
    ax.hlines(y, row["or_lo90"], row["or_hi90"], color=col, lw=5, alpha=0.85)
    ax.plot(row["or"], y, "o", color="white", mec=col, mew=2, ms=8, label=label, zorder=3)


def _or_ticks(ax):
    ticks = [0.8, 0.9, 1.0, 1.1, 1.25, 1.5]
    lo, hi = ax.get_xlim()
    ticks = [x for x in ticks if lo <= x <= hi] or [1.0]
    ax.set_xticks(ticks, [f"{x:g}".replace(".", ",") for x in ticks])
    ax.minorticks_off()


def forest(ctx: Ctx) -> pd.DataFrame:
    main_rows = [dict(r, spec="main") for r in ctx.res.get("main_table", [])]
    sens = ctx.res.get("sensitivity_table", [])
    allrows = pd.DataFrame(main_rows + sens)
    allrows = allrows[allrows["label"] != C.NOT_ESTIMATED]
    specs = [s for s in SPEC_LABELS if s in set(allrows["spec"])]
    colors = {"M1": F.VERMILION, "M2": F.BLUE, "M3": F.GREEN}
    off = {"M1": -0.25, "M2": 0.0, "M3": 0.25}
    fig, ax = plt.subplots(figsize=(10, 5.6))
    _margin_band(ax, ctx.p.margin)
    seen = set()
    for i, s in enumerate(specs):
        for _, row in allrows[allrows["spec"] == s].iterrows():
            m = row["model"]
            lab = (
                {"M1": "M1 GLMM", "M2": "M2 pooled, klastr. 2-kier.", "M3": "M3 FE nadawcy"}[m]
                if m not in seen
                else None
            )
            seen.add(m)
            _ci(ax, i + off[m], row, colors[m], lab)
    ax.set_yticks(range(len(specs)), [SPEC_LABELS[s] for s in specs], fontsize=12)
    ax.invert_yaxis()
    ax.set_xscale("log")
    _or_ticks(ax)
    ax.set_xlabel("OR prawego swipe'a: bio vs brak bio (skala log)")
    ax.set_title("H3a: OR dla has_bio we wszystkich specyfikacjach")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, fontsize=11)
    ax.grid(axis="y", visible=False)
    out = allrows[["spec", "model", "or", "or_lo95", "or_hi95", "or_lo90", "or_hi90", "label"]]
    ctx.saver.save_fig(
        fig,
        "h3a_03_forest_has_bio",
        out.assign(margin_lo=math.exp(-ctx.p.margin), margin_hi=math.exp(ctx.p.margin)),
        caption="Rys. F3. OR dla has_bio (bio odbiorcy niepuste vs puste) w modelu głównym i "
        "analizach wrażliwości; cienki słupek 95% CI, gruby 90% CI; szary pas: margines "
        "praktycznego zera [e^-0,10; e^0,10]. lme4 pominięty (brak R).",
        model="M1/M2/M3, S1-S7",
        n_swipes=len(ctx.main),
        n_receivers=ctx.main["r_key"].nunique(),
    )
    plt.show()
    return out


# ============================================================================ lme4


def lme4_crosscheck(ctx: Ctx) -> dict:
    """glmer(nAGQ = 0) with crossed (1|sender) + (1|receiver) on the main spec, if R is there.

    Data go through a parquet file in a temporary directory that is removed afterwards.
    Note: this branch could not be tested in the build environment (no R installed).
    """
    import tempfile

    if not shutil.which("Rscript"):
        res = {"status": "skipped", "reason": "Rscript not found"}
    else:
        chk = subprocess.run(
            ["Rscript", "-e", "library(lme4); library(arrow)"], capture_output=True, text=True
        )
        if chk.returncode:
            res = {"status": "skipped", "reason": "R packages lme4/arrow missing"}
        else:
            X, y, s, r, names, _ = _arrays(ctx.main, M.Spec())
            cols = [f"x{i}" for i in range(1, len(names))]
            df = pd.DataFrame(X[:, 1:], columns=cols).assign(y=y, sender=s, receiver=r)
            with tempfile.TemporaryDirectory() as td:
                pq = Path(td) / "d.parquet"
                df.to_parquet(pq)
                form = "y ~ " + " + ".join(cols) + " + (1|sender) + (1|receiver)"
                code = (
                    f"library(lme4); library(arrow); d <- read_parquet('{pq}'); "
                    "d$sender <- factor(d$sender); d$receiver <- factor(d$receiver); "
                    f"m <- glmer({form}, data = d, family = binomial, nAGQ = 0); "
                    "s <- summary(m)$coefficients; "
                    "cat(sprintf('%.10g,%.10g\\n', s[,1], s[,2]), sep='')"
                )
                try:
                    out = subprocess.run(
                        ["Rscript", "-e", code],
                        capture_output=True,
                        text=True,
                        timeout=ctx.runner.timeout_s,
                    )
                    vals = [list(map(float, ln.split(","))) for ln in out.stdout.split()]
                    res = {
                        "status": "ok" if out.returncode == 0 else "failed",
                        "names": names,
                        "coef": [v[0] for v in vals],
                        "se": [v[1] for v in vals],
                    }
                except subprocess.TimeoutExpired:
                    res = {"status": "timeout"}
    ctx.res["lme4"] = res
    ctx.runner.log_time("lme4_crosscheck", 0.0, res["status"])
    persist(ctx)
    return res
