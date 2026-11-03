"""Automatic `summary.md` for H3a (Polish, aggregates only)."""

from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from rentfriends.h3a import classify as C


def _f(x, nd=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    return f"{x:.{nd}f}".replace(".", ",")


def _or_ci(r: dict, nd=3) -> str:
    if not r or "or" not in r or r.get("or") is None:
        return "brak oszacowania"
    return (
        f"{_f(r['or'], nd)} (95% CI {_f(r['or_lo95'], nd)}–{_f(r['or_hi95'], nd)}; "
        f"90% CI {_f(r['or_lo90'], nd)}–{_f(r['or_hi90'], nd)})"
    )


def lme4_label(res: dict, margin: float) -> str | None:
    l4 = res.get("lme4", {})
    if l4.get("status") != "ok" or "has_bio" not in l4.get("names", []):
        return None
    i = l4["names"].index("has_bio")
    return C.classify(l4["coef"][i], l4["se"][i], margin)


def agent_defaults(decision_log: Path) -> list[str]:
    if not decision_log.exists():
        return []
    out = []
    for line in decision_log.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##+\s+(D-H3a-\d+.*\[default agenta\].*)$", line)
        if m:
            out.append(m.group(1))
    return out


LIMITATIONS = [
    "Związek ≠ przyczynowość: wynik opisuje współwystępowanie bio i prawego swipe'a w "
    "obserwowanej ekspozycji, nie efekt napisania bio.",
    "Brak zdjęć: popularność odbiorcy jest kontrolowana tylko jako efekt losowy (M1); założenie "
    "niezależności efektu losowego od has_bio jest wątłe (zdjęcia i staranność profilu mogą iść "
    "w parze).",
    "Ekspozycja przez feed: nie znamy algorytmu rankingu i filtrów; kto komu się wyświetla, "
    "może zależeć od profilu (także od bio).",
    "Czas tylko w dniach: wersja profilu przypisana regułą as-of (D7); swipe'y z dnia zmiany są "
    "przypisane do wersji sprzed dnia.",
    "Próba samoselekcyjna i jednorodna (studenci, głównie 18-20 lat, kilka miast); brak "
    "uogólnienia na wszystkich szukających współlokatora. Match ≠ najem.",
    "Pola stylu życia mają duże braki (74-81% w 5 z 7 pól); `profile_completeness` jest więc "
    "grubą miarą staranności profilu.",
    "Mapowanie tagów (`interests_mapping.csv`) nie jest zrecenzowane przez człowieka; liczba "
    "tagów jest prowizoryczna (stąd S6).",
    "Widoczność bio na karcie profilu: informacja od Dominika, brak potwierdzenia dostawcy.",
]


def write_summary(
    res: dict,
    report_dir: str | Path,
    level: int,
    decision_log: Path = Path("docs/h3a/decision-log.md"),
) -> Path:
    report_dir = Path(report_dir)
    p = res.get("params", {})
    margin = p.get("margin", 0.10)
    v = res.get("verdict", {})
    l4 = lme4_label(res, margin)
    final = v.get("final", "brak")
    if l4 is not None and C.ESTIMATOR_SENSITIVE not in final and l4 != v.get("label_M1"):
        final = f"{final}; {C.ESTIMATOR_SENSITIVE} (lme4: {l4})"
    mt = {r["model"]: r for r in res.get("main_table", [])}
    L = []
    L.append("# H3a: wyniki (generowane automatycznie)\n")
    L.append(
        f"Wygenerowano: {datetime.now().isoformat(timespec='minutes')}; poziom przebiegu: "
        f"{level}; SAMPLE_FRAC = {p.get('sample_frac')}; SEED = {p.get('seed')}; "
        f"margines praktycznego zera |log OR| ≤ {_f(margin, 2)}.\n"
    )
    if p.get("sample_frac", 1.0) < 1.0:
        L.append("> **Uwaga: przebieg na próbie (smoke test). Liczby nie są wynikiem badania.**\n")
    L.append("## Werdykt\n")
    L.append(f"**Etykieta końcowa: {final}**\n")
    L.append(f"- M1 (GLMM, skrzyżowane efekty losowe): {v.get('label_M1')}")
    L.append(f"- M2 (pooled logit, klastrowanie dwukierunkowe): {v.get('label_M2')}")
    L.append(f"- M3 (FE nadawcy, klastrowanie po odbiorcy; poza regułą): {v.get('label_M3')}")
    L.append(
        f"- lme4: {res.get('lme4', {}).get('status', 'nie uruchomiony')} "
        f"({res.get('lme4', {}).get('reason', '')})\n"
    )
    L.append("## Wynik główny (has_bio: bio odbiorcy niepuste vs puste)\n")
    L.append("| Model | OR (95% CI; 90% CI) | β | SE | p | MDE OR | Etykieta |")
    L.append("|---|---|---|---|---|---|---|")
    for m in ("M1", "M2", "M3"):
        r = mt.get(m, {})
        L.append(
            f"| {m} | {_or_ci(r)} | {_f(r.get('beta'), 4)} | {_f(r.get('se'), 4)} | "
            f"{_f(r.get('p'), 4)} | {_f(r.get('mde_or'))} | {r.get('label', '–')} |"
        )
    ame = v.get("ame_M2", {})
    if ame:
        L.append(
            f"\nŚredni efekt krańcowy (M2, populacyjny): {_f(ame.get('ame_pp'), 2)} p.p. "
            f"(95% CI {_f(ame.get('lo95_pp'), 2)}–{_f(ame.get('hi95_pp'), 2)} p.p.; SE "
            "z klastrowaniem dwukierunkowym, delta method)."
        )
    d1 = res.get("m1_diag", {})
    L.append("\n## Estymator M1: zbieżność i czasy\n")
    att = d1.get("attempts") or []
    n_conv = sum(1 for a in att if a.get("convergence_status") == 0)
    m1 = res.get("fits", {}).get("main", {}).get("M1", {})
    if d1.get("status") != "ok" and "has_bio" in m1.get("names", []):
        b = m1["coef"][m1["names"].index("has_bio")]
        L.append(
            f"- **Optymalizacja zbieżna w {n_conv}/{len(att)} próbach, ale GPBoost nie policzył "
            "SE (numeryczny Hessian nie jest dodatnio określony), więc M1 nie ma CI ani etykiety; "
            f"zadziałał fallback z §6 promptu.** Oszacowanie punktowe z ostatniej próby: "
            f"β = {_f(b, 4)}, OR = {_f(math.exp(b))} (bez SE, nie do wnioskowania)."
        )
    L.append(
        f"- status: {d1.get('status')}; optymalizator: {d1.get('optimizer')}; "
        f"kod zbieżności GPBoost: {d1.get('convergence_status')} (0 = zbieżny); "
        f"iteracje: {d1.get('n_iter')}; czas fitu: {_f(d1.get('time_s'), 1)} s"
    )
    L.append(
        f"- wariancja efektu losowego nadawcy: {_f(d1.get('var_sender'))} "
        f"(SE {_f(d1.get('var_sender_se'))}); odbiorcy: {_f(d1.get('var_receiver'))} "
        f"(SE {_f(d1.get('var_receiver_se'))}); log-likelihood (Laplace): "
        f"{_f(d1.get('loglik'), 1)}"
    )
    if d1.get("attempts"):
        L.append(f"- próby optymalizatorów: {d1.get('attempts')}")
    san = res.get("sanity", {})
    if san:
        L.append(
            f"- sanity check (symulacja na rzeczywistym designie, {san.get('n_ok')}/"
            f"{san.get('n_reps')} fitów OK): β_bio prawdziwe {_f(san.get('true_beta_bio'))}, "
            f"średnie {_f(san.get('mean_beta_bio'))}, obciążenie "
            f"{_f(san.get('bias_beta_bio'), 4)}; SD empiryczne "
            f"{_f(san.get('emp_sd_beta_bio'), 4)} vs średni SE "
            f"{_f(san.get('mean_se_beta_bio'), 4)}; pokrycie 95% CI "
            f"{_f(san.get('coverage95_beta_bio'), 2)}; wariancje "
            f"{_f(san.get('mean_var_sender'))}/{_f(san.get('true_var_sender'))} (nadawca), "
            f"{_f(san.get('mean_var_receiver'))}/{_f(san.get('true_var_receiver'))} (odbiorca)"
        )
    L.append("\n## Przepływ próby\n")
    if res.get("flow"):
        L.append(pd.DataFrame(res["flow"]).to_markdown(index=False))
    hy = res.get("hyderabad", {})
    L.append(
        f"\nHyderabad: {hy.get('accounts')} kont; usuwa {hy.get('profile_swipes_removed')} "
        f"swipe'ów na profile (jako nadawca {hy.get('as_sender')}, jako odbiorca "
        f"{hy.get('as_receiver')})."
    )
    L.append("\n## M5: długość bio (drugorzędne, bez werdyktu)\n")
    for r in res.get("m5", []):
        L.append(
            f"- {r['model']}: OR na podwojenie długości {_f(r.get('or_doubling'))} (95% CI "
            f"{_f(r.get('or_doubling_lo95'))}–{_f(r.get('or_doubling_hi95'))}); "
            f"OR dla sufitu 250 znaków {_f(r.get('or_cap'))} (95% CI "
            f"{_f(r.get('or_cap_lo95'))}–{_f(r.get('or_cap_hi95'))})"
        )
    m6 = res.get("m6", {})
    if m6:
        L.append("\n## M6: przyrost predykcyjny (opisowy)\n")
        L.append(
            f"- ΔlogLoss = {m6['d_logloss']:.2e} (95% CI {m6['d_logloss_lo95']:.2e} do "
            f"{m6['d_logloss_hi95']:.2e}); ΔAUC = {m6['d_auc']:.2e} (95% CI "
            f"{m6['d_auc_lo95']:.2e} do {m6['d_auc_hi95']:.2e}); AUC baseline "
            f"{_f(m6['auc_base'])}. Wnioskowanie opiera się na regule z sekcji 7, nie na M6."
        )
    m4 = res.get("m4", {})
    if m4:
        fu = m4["funnel"]
        L.append("\n## M4: analiza w obrębie odbiorcy\n")
        L.append(
            f"- lejek: {fu['receivers_in_sample']} odbiorców → {fu['with_bio_text_change']} "
            f"ze zmianą tekstu bio → {fu['with_status_change']} ze zmianą pusty↔niepusty → "
            f"{fu['with_min_swipes_each_side']} z ≥ 5 swipe'ami po każdej stronie "
            f"(próg {fu['gate_threshold']}); wariant „bez zmian innych pól”: "
            f"{m4['funnel_clean']['with_min_swipes_each_side']}."
        )
        if "verdict" in m4:
            L.append(f"- **{m4['verdict']}**.")
        if "lpm" in m4:
            lp = m4["lpm"]
            L.append(
                f"- LPM (FE odbiorcy i tygodnia): {_f(lp['beta_pp'], 2)} p.p. (95% CI "
                f"{_f(lp['lo95_pp'], 2)}–{_f(lp['hi95_pp'], 2)}), {lp['n_receivers']} "
                "odbiorców."
            )
    st = res.get("sensitivity_table", [])
    if st:
        L.append("\n## Analizy wrażliwości S1-S7\n")
        df = pd.DataFrame(st)
        df["OR (95% CI)"] = [_or_ci(r) for r in st]
        L.append(df[["spec", "model", "n_obs", "OR (95% CI)", "label"]].to_markdown(index=False))
        flags = []
        for s in df["spec"].unique():
            labs = set(df.loc[df["spec"] == s, "label"])
            if len(labs) > 1:
                flags.append(f"{s}: różne etykiety między estymatorami ({'; '.join(sorted(labs))})")
        diff_main = sorted(
            set(df.loc[(df["model"] == "M2") & (df["label"] != v.get("label_M2")), "spec"])
        )
        if diff_main:
            flags.append(f"etykieta M2 inna niż w specyfikacji głównej w: {', '.join(diff_main)}")
        if flags:
            L.append("\nFlagi wrażliwości: " + " | ".join(flags))
    s8 = res.get("s8", {})
    if s8:
        L.append("\n## S8: płeć nadawcy\n")
        for sx, d in s8["strata"].items():
            if "skipped" in d:
                L.append(f"- {sx}: pominięte ({d['skipped']})")
            else:
                L.append(
                    f"- {sx}: M2 {_or_ci(d['M2'])} [{d['M2']['label']}]; "
                    f"M3 {_or_ci(d['M3'])} [{d['M3']['label']}]"
                )
        it = s8["interaction"]
        L.append(
            f"- test interakcji has_bio × płeć nadawcy (Wald, df = {it['df']}): "
            f"χ² = {_f(it['wald_chi2'], 2)}, p = {_f(it['p'], 4)}"
        )
    cc = res.get("card_check", [])
    if cc:
        L.append("\n## Kontrola zgodności z kartą M1\n")
        L.append(pd.DataFrame(cc).to_markdown(index=False))
    defs = agent_defaults(decision_log)
    if defs:
        L.append("\n## Decyzje oznaczone [default agenta]\n")
        L += [f"- {d}" for d in defs]
    L.append("\n## Ograniczenia, które muszą towarzyszyć wynikowi\n")
    L += [f"- {x}" for x in LIMITATIONS]
    text = "\n".join(L) + "\n"
    (report_dir / f"summary_level{level}.md").write_text(text, encoding="utf-8")
    path = report_dir / "summary.md"
    path.write_text(text, encoding="utf-8")
    return path
