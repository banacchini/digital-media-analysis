"""Level 3 exports for the person laying out the slides: numbers JSON, captions, summary.

`h3a_numbers.json` is the single source of numbers; every numeric leaf `k` has a sibling `k_pl`
(Polish formatting: decimal comma, non-breaking spaces). Aggregates only.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

NBSP = " "
INT_KEYS = ("n", "n_obs", "n_swipes", "n_senders", "n_receivers", "swipes", "prawe", "nadawcy")


def fmt_pl(x: float, nd: int = 2) -> str:
    """Polish number: decimal comma, non-breaking space as thousands separator."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    s = f"{x:,.{nd}f}".replace(",", NBSP).replace(".", ",")
    return s.replace("-", "−")


def _leaf_pl(key: str, v: float) -> str:
    k = key.lower()
    if isinstance(v, int) or k in INT_KEYS or k.startswith("n_"):
        return fmt_pl(float(v), 0)
    if k == "p" or k.endswith("_p") or k.startswith("p_value"):
        return "<0,001" if v < 0.001 else fmt_pl(v, 3)
    if "pct" in k or k.endswith("pp") or "_pp" in k or k.startswith(("lo", "hi")):
        return fmt_pl(v, 1)
    if k.startswith(("beta", "se", "coef")) or k in ("chi2", "stat"):
        return fmt_pl(v, 3)
    return fmt_pl(v, 2)


def add_pl(obj):
    """Return a copy where each numeric leaf of a dict gets a `*_pl` sibling."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = add_pl(v)
            if isinstance(v, int | float) and not isinstance(v, bool):
                out[f"{k}_pl"] = _leaf_pl(str(k), v)
        return out
    if isinstance(obj, list):
        return [add_pl(v) for v in obj]
    return obj


def _row_or(r: dict | None) -> dict | None:
    if not r or r.get("or") is None:
        return None
    keys = ("or", "or_lo95", "or_hi95", "or_lo90", "or_hi90", "beta", "se", "p", "label")
    return {k: r.get(k) for k in keys if k in r}


def build_numbers(res: dict, theme: dict | None = None) -> dict:
    """Collect all numbers used on the figures and in the result summary."""
    fits = res.get("fits", {})
    main_fit = fits.get("main", {})
    out: dict = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "seed": res.get("params", {}).get("seed"),
            "data_hash": (main_fit.get("M2") or {}).get("_fingerprint"),
            "margin_log_or": res.get("params", {}).get("margin"),
            "n_swipes": main_fit.get("n_obs"),
            "n_senders": main_fit.get("n_senders"),
            "n_receivers": main_fit.get("n_receivers"),
            "flow": res.get("flow"),
        },
        "verdict": res.get("verdict", {})
        | {"ame_M2": (res.get("verdict", {}) or {}).get("ame_M2")},
    }
    mt = {r["model"]: r for r in res.get("main_table", [])}
    out["main"] = {m: _row_or(mt.get(m)) for m in ("M2", "M3")}
    m1 = main_fit.get("M1", {})
    if m1.get("names") and "has_bio" in m1["names"]:
        b = m1["coef"][m1["names"].index("has_bio")]
        out["main"]["M1_gpboost_point"] = {
            "beta": b,
            "or": math.exp(b),
            "se_available": bool(m1.get("status") == "ok"),
            "var_sender": m1.get("var_sender"),
            "var_receiver": m1.get("var_receiver"),
        }
    l4 = res.get("lme4", {})
    if l4.get("status") == "ok":
        out["main"]["M1_lme4"] = {
            "label": l4.get("label"),
            **(l4.get("has_bio_wald") or {}),
            "var_sender": l4["var_sender"],
            "var_receiver": l4["var_receiver"],
            "lrt_stat": l4.get("lrt_stat"),
            "lrt_p": l4.get("lrt_p"),
            "singular": l4.get("singular"),
        }
    b1 = res.get("b1", {})
    if b1.get("status") == "ok":
        out["main"]["M1_gpboost_lrt"] = {
            "stat": b1["lrt"]["stat"],
            "p": b1["lrt"]["p"],
            "profile_ci": b1.get("profile_ci"),
            "profile_label": b1.get("profile_label"),
        }
    a5 = res.get("a5", {})
    out["a5"] = {
        "strata": {k: v for k, v in a5.get("strata", {}).items() if "p0" in v},
        "by_spec": [
            {
                "spec": r["spec"],
                "label": r["label"],
                "n_obs": r["n_obs"],
                "ame_m2": r["ame_m2"],
                "m3_pp": r["m3_pp"],
            }
            for r in a5.get("by_spec", [])
        ],
        "m3_pp_note": "M3 (FE nadawcy) przeliczone na p.p. przy ryzyku bazowym z M2.",
    }
    out["sensitivity"] = res.get("sensitivity_table")
    s8 = res.get("s8", {})
    out["s8"] = {
        "strata": {
            k: {m: _row_or(v.get(m)) for m in ("M2", "M3")}
            for k, v in s8.get("strata", {}).items()
            if "M2" in v
        },
        "interaction": s8.get("interaction"),
    }
    out["m4"] = res.get("m4", {}).get("funnel")
    out["m5"] = res.get("m5")
    out["m6"] = {k: v for k, v in (res.get("m6") or {}).items() if not k.startswith("_")}
    for k in ("a1", "a2", "a3", "a4", "b1", "b3", "b_report"):
        if k in res:
            out[k] = res[k]
    out["m1_status"] = {
        "gpboost_se": bool(m1.get("status") == "ok"),
        "gpboost_status": m1.get("status"),
        "lme4_status": l4.get("status"),
    }
    if theme:
        out["theme"] = theme
    return add_pl(out)


def write_numbers(res: dict, export_dir: str | Path, theme: dict | None = None) -> Path:
    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / "h3a_numbers.json"
    path.write_text(
        json.dumps(build_numbers(res, theme), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return path


# ============================================================================ captions


def _pp(d: dict) -> str:
    return (
        f"{fmt_pl(d['pct'], 1)}{NBSP}p.p. (95%: {fmt_pl(d['lo95'], 1)} do {fmt_pl(d['hi95'], 1)})"
    )


def write_captions(res: dict, export_dir: str | Path) -> Path:
    a5 = res["a5"]
    F, M = a5["strata"]["F"], a5["strata"]["M"]
    by = {r["spec"]: r for r in a5["by_spec"]}
    s2a = by.get("S2a")
    lim = (
        "Związek, nie przyczyna (dane obserwacyjne z jednej aplikacji); brak zdjęć profilowych w "
        "danych; ekspozycja profili zależy od feedu aplikacji"
    )
    l4 = res.get("lme4", {})
    if l4.get("status") == "ok":
        lim += "; model z efektami losowymi: oszacowanie z `lme4` (GPBoost nie podał błędów std.)"
    else:
        lim += "; model z efektami losowymi bez błędów standardowych"
    lim += "."
    L = ["# H3a: podpisy, teksty alternatywne i tytuły-wnioski (do składu w Typst)\n"]
    L.append(
        "Wszystkie liczby: `h3a_numbers.json`. Tytuły są ułożone od najostrożniejszego do "
        "najbardziej odważnego; każdy jest zgodny z wynikami.\n"
    )
    L.append("## Figura A: bez bio vs z bio\n")
    L.append(
        f"**Podpis.** Odsetek prawych swipe'ów dla profili bez bio i z bio, osobno dla kobiet i "
        f"mężczyzn oceniających profile (model z kontrolą płci, wieku, miasta, kompletności "
        f"profilu i liczby zainteresowań). Kobiety: {fmt_pl(F['p0']['pct'], 1)}% → "
        f"{fmt_pl(F['p1']['pct'], 1)}%, różnica {_pp(F['diff'])}. Mężczyźni: "
        f"{fmt_pl(M['p0']['pct'], 1)}% → {fmt_pl(M['p1']['pct'], 1)}%, różnica {_pp(M['diff'])}. "
        "Wartości wyświetlane z zaokrągleniem do 0,1; różnica liczona z niezaokrąglonych.\n"
    )
    L.append(
        "**Tekst alternatywny.** Dwa panele ze strzałką od szarego punktu (bez bio) do "
        "niebieskiego "
        f"(z bio). U kobiet strzałka rośnie z {fmt_pl(F['p0']['pct'], 1)}% do "
        f"{fmt_pl(F['p1']['pct'], 1)}%; u mężczyzn niemal płasko, z {fmt_pl(M['p0']['pct'], 1)}% "
        f"do {fmt_pl(M['p1']['pct'], 1)}%.\n"
    )
    L.append("**Tytuły-wnioski:**\n")
    L.append("1. Różnicę widać u kobiet; u mężczyzn nie da się jej odróżnić od zera.")
    L.append(
        f"2. Kobiety swipe'ują w prawo profile z bio o ok. {fmt_pl(F['diff']['pct'], 0)} p.p. "
        "częściej; u mężczyzn brak wyraźnej różnicy."
    )
    L.append("3. Bio w profilu wiąże się z większą liczbą prawych swipe'ów kobiet, nie mężczyzn.\n")
    L.append(f"**Ograniczenia.** {lim}\n")
    L.append("## Figura B: na 100 swipe'ów\n")
    L.append(
        "**Podpis.** To samo co na figurze A, w postaci 100 swipe'ów na profile: kolorowe kropki "
        "to prawe swipe'y, szare to lewe (ułamek kropki oddaje część dziesiętną). Zakresy: "
        "95% CI (delta method, klastrowanie po nadawcy i odbiorcy).\n"
    )
    L.append(
        "**Tekst alternatywny.** Cztery siatki 10 × 10 kropek: kobiety bez bio "
        f"({fmt_pl(F['p0']['pct'], 1)} kolorowych), kobiety z bio ({fmt_pl(F['p1']['pct'], 1)}), "
        f"mężczyźni bez bio ({fmt_pl(M['p0']['pct'], 1)}), mężczyźni z bio "
        f"({fmt_pl(M['p1']['pct'], 1)}).\n"
    )
    L.append("**Tytuły-wnioski:**\n")
    L.append("1. Na 100 swipe'ów kobiet: ok. 14 w prawo bez bio, ok. 17 z bio.")
    L.append("2. Na każde 100 profili z bio kobiety zaznaczają w prawo ok. 3 więcej niż bez bio.")
    L.append(
        "3. Profil z bio dostaje od kobiet około trzech dodatkowych prawych swipe'ów na 100.\n"
    )
    L.append(f"**Ograniczenia.** {lim}\n")
    L.append("## Figura C: czy wynik się trzyma?\n")
    s2a_txt = ""
    if s2a:
        d = s2a["ame_m2"]
        s2a_txt = (
            "W połowie próby (tylko swipe'y z pewną wersją profilu) efekt jest słabszy: "
            + _pp({"pct": d["ame_pp"], "lo95": d["lo95_pp"], "hi95": d["hi95_pp"]})
            + (", przedział obejmuje zero. " if d["lo95_pp"] <= 0 else ". ")
        )
    L.append(
        "**Podpis.** Średni efekt bio w punktach procentowych (kółko: model dla wszystkich "
        "swipe'ów; romb: porównanie w obrębie jednej osoby oceniającej, przeliczone na p.p. przy "
        "ryzyku bazowym z M2) w modelu podstawowym i w sprawdzeniach odporności. Pas: ±1,5 p.p., "
        "orientacyjny odpowiednik marginesu praktycznego zera z reguły werdyktu. "
        f"{s2a_txt}\n"
    )
    exceptions = [r["label"] for r in by.values() if r["ame_m2"]["lo95_pp"] <= 0]
    L.append(
        f"**Tekst alternatywny.** {len(by)} wierszy; kółka leżą głównie na prawo od pasa wokół "
        "zera, z przedziałami po dodatniej stronie. Przedział obejmuje zero w: "
        + ("; ".join(exceptions) or "żadnym wierszu")
        + ".\n"
    )
    L.append("**Tytuły-wnioski:**\n")
    L.append("1. Wynik jest podobny w większości sprawdzeń, ale słabszy w połowie próby.")
    main_ame = by["main"]["ame_m2"]["ame_pp"]
    L.append(
        f"2. W większości sprawdzeń bio wiąże się z o ok. {fmt_pl(main_ame, 0)} p.p. częstszymi "
        "prawymi swipe'ami; słabszy efekt w połowie próby i u mężczyzn."
    )
    pos = sum(1 for r in by.values() if r["ame_m2"]["lo95_pp"] > 0)
    L.append(f"3. Związek bio z prawym swipe'em utrzymuje się w {pos} z {len(by)} sprawdzeń.\n")
    L.append(f"**Ograniczenia.** {lim}\n")
    path = Path(export_dir) / "h3a_captions.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path


# ============================================================================ summary


def _orci(r: dict | None, nd: int = 2) -> str:
    if not r or r.get("or") is None or r.get("or") != r.get("or"):
        return "brak oszacowania"
    return f"{fmt_pl(r['or'], nd)} ({fmt_pl(r['or_lo95'], nd)}–{fmt_pl(r['or_hi95'], nd)})"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out + [""]


def write_summary3(res: dict, report_dir: str | Path, export_files: list[str]) -> Path:
    POST = "diagnostyka post hoc, zainicjowana wynikiem S2a; bez poprawek na wielokrotność"
    v = res.get("verdict", {})
    L = ["# H3a, poziom 3: diagnostyka, błędy standardowe GLMM, figury (generowane)\n"]
    L.append(f"Wygenerowano: {datetime.now().isoformat(timespec='minutes')}.\n")
    L.append("## 1. Co zmienia się względem poziomu 2\n")
    L.append(
        f"- Etykieta z poziomu 2 pozostaje: **{v.get('final')}**. Reguła werdyktu, margines 0,10 "
        "i lista S1-S8 bez zmian.\n"
        "- Nowe: dla M1 (GLMM) są teraz błędy standardowe i CI z dwóch niezależnych źródeł "
        "(sekcja 3), więc reguła zgodności M1 = M2 mogła zostać sprawdzona.\n"
        "- Adnotacja do S2a: efekt w połowie próby z `prior_version` jest słabszy (sekcja 2, A2).\n"
    )
    # ---- A
    L.append(f"## 2. Blok A ({POST}; S8 była zaplanowana)\n")
    a1 = res.get("a1", {})
    L.append("### A1. Wszystkie próby optymalizatora GPBoost (specyfikacja główna)\n")
    rows = [
        [
            a["config"],
            str(a["convergence_code"]),
            fmt_pl(a["beta_has_bio"], 4) if a["beta_has_bio"] is not None else "–",
            fmt_pl(a["var_sender"], 2) if a["var_sender"] is not None else "–",
            fmt_pl(a["var_receiver"], 3) if a["var_receiver"] is not None else "–",
            fmt_pl(a["loglik"], 1) if a["loglik"] is not None else "–",
            fmt_pl(a["time_s"], 1) if a["time_s"] is not None else "–",
        ]
        for a in a1.get("attempts", [])
    ]
    L += _table(
        [
            "konfiguracja",
            "kod zbieżności",
            "β has_bio",
            "wariancja nadawcy",
            "wariancja odbiorcy",
            "log-lik.",
            "czas [s]",
        ],
        rows,
    )
    rng = a1.get("beta_range_converged")
    if rng:
        mid = sum(rng) / 2
        closer = "M3" if abs(mid - a1["beta_m3"]) < abs(mid - a1["beta_m2"]) else "M2"
        L.append(
            f"β zbieżnych prób: {fmt_pl(rng[0], 4)} do {fmt_pl(rng[1], 4)}; M2: "
            f"{fmt_pl(a1['beta_m2'], 4)}, M3: {fmt_pl(a1['beta_m3'], 4)}. Oszacowanie GLMM jest "
            f"bliższe {closer}. "
            + (
                ""
                if closer == "M3"
                else "Oczekiwanie z promptu (β bliżej M3 przy wariancji nadawcy ≈ 7,8) nie "
                "potwierdziło się; zapisano jako anomalię w decision-logu. "
            )
            + "Żadna próba nie dała SE dla współczynników.\n"
        )
    a2 = res.get("a2", {})
    L.append("### A2. Heterogeniczność wg pochodzenia cech i „wieku” konta (diagnoza S2a)\n")
    rows = []
    for r in a2.get("rows", []):
        rows.append(
            [
                r["spec"],
                r["grupa"],
                r["model"],
                _orci(r),
                fmt_pl(r.get("n_obs", 0), 0),
                r.get("label", ""),
            ]
        )
    L += _table(["wymiar", "grupa", "model", "OR (95% CI)", "n swipe'ów", "etykieta"], rows)
    ints = []
    for name, key in (
        ("pochodzenie cech (prior_version × has_bio)", "asof_interaction"),
        ("dzień konta nadawcy (kosze 0 / 1-7 / ≥ 8)", "sb_interaction"),
        ("wiek profilu odbiorcy (kosze 0 / 1-7 / ≥ 8)", "rb_interaction"),
    ):
        it = a2.get(key, {})
        for m in ("M2", "M3"):
            x = it.get(m, {})
            if x.get("status") == "ok":
                ints.append([name, m, fmt_pl(x["chi2"], 2), str(x["df"]), fmt_pl(x["p"], 3)])
    L += _table(["interakcja z has_bio", "model", "χ² Walda", "df", "p"], ints)
    ex = a2.get("excluded_no_history", {})
    L.append(
        f"Wyłączone z analiz wieku: {ex.get('rows')} swipe'ów, {ex.get('users_in_main_sample')} "
        "użytkowników bez historii profilu.\n"
    )
    L.append("### A3. Stabilność OR po dodawaniu kontroli\n")
    L += _table(
        ["krok", "model", "OR (95% CI)"],
        [[r["krok"], r["model"], _orci(r, 3)] for r in res.get("a3", {}).get("rows", [])],
    )
    L.append("### A4. E-value (przybliżenie RR ≈ √OR)\n")
    L += _table(
        ["grupa", "model", "OR", "E-value punktu", "E-value granicy CI"],
        [
            [
                r["grupa"],
                r["model"],
                fmt_pl(r["or"], 3),
                fmt_pl(r["e_point"], 2),
                fmt_pl(r["e_ci_limit"], 2),
            ]
            for r in res.get("a4", {}).get("rows", [])
        ],
    )
    L.append(
        "Założenia: wynik częsty (baza ≈ 20%), `E = RR + √(RR(RR−1))`. To miara czułości, nie "
        "dowód braku konfundowania; E-value 1,00 oznacza przedział obejmujący 1.\n"
    )
    a5 = res.get("a5", {})
    L.append("### A5. Prawdopodobieństwa standaryzowane i średni efekt krańcowy (M2)\n")
    rows = []
    names = {"all": "wszyscy", "F": "kobiety", "M": "mężczyźni"}
    for k, sp in a5.get("strata", {}).items():
        if "p0" not in sp:
            continue
        rows.append(
            [
                names[k],
                fmt_pl(sp["p0"]["pct"], 1) + "%",
                fmt_pl(sp["p1"]["pct"], 1) + "%",
                f"{fmt_pl(sp['diff']['pct'], 2)} ({fmt_pl(sp['diff']['lo95'], 2)} do "
                f"{fmt_pl(sp['diff']['hi95'], 2)})",
                f"{sp['per100_p0']} → {sp['per100_p1']}".replace(".", ","),
            ]
        )
    L += _table(["warstwa", "bez bio", "z bio", "różnica w p.p. (95% CI)", "na 100 swipe'ów"], rows)
    L.append("Warstwa „inna płeć” pominięta (za mało danych, jak w S8).\n")
    rows = []
    for r in a5.get("by_spec", []):
        m3 = r.get("m3_pp")
        rows.append(
            [
                r["spec"],
                r["label"],
                fmt_pl(r["ame_m2"]["ame_pp"], 2),
                f"{fmt_pl(r['ame_m2']['lo95_pp'], 2)} do {fmt_pl(r['ame_m2']['hi95_pp'], 2)}",
                fmt_pl(m3["pct"], 2) if m3 else "–",
            ]
        )
    L += _table(["spec", "opis", "AME M2 [p.p.]", "95% CI", "M3 przeliczone [p.p.]"], rows)
    L.append(
        "M3 (FE nadawcy) nie ma efektu krańcowego w populacji; kolumna „przeliczone” stosuje β z "
        "M3 do ryzyk bazowych z M2 (szacunek orientacyjny, CI z granic β).\n"
    )
    # ---- B
    L.append("## 3. Blok B: błędy standardowe dla GLMM (M1)\n")
    br = res.get("b_report", {})
    L += _table(
        ["szczebel", "co uzyskano", "β", "SE lub p", "CI", "status"],
        [
            [
                r["szczebel"],
                r["co_uzyskano"],
                fmt_pl(r["beta"], 4) if r["beta"] is not None else "–",
                r["se_lub_p"].replace(".", ","),
                r["ci"].replace(".", ","),
                str(r["status"]).replace(".", ","),
            ]
            for r in br.get("ladder", [])
        ],
    )
    for k, a in br.get("agreement", {}).items():
        L.append(
            f"- Reguła zgodności M1 = M2 ({k}): M1 **{a['label_m1']}**, M2 **{a['label_m2']}** → "
            + ("**zgodne**." if a["zgodne"] else "**niezgodne** (oznacz: wrażliwy na estymator).")
        )
    l4 = res.get("lme4", {})
    if l4.get("status") == "ok":
        L.append(
            f"- lme4: wariancja nadawcy {fmt_pl(l4['var_sender'], 2)}, odbiorcy "
            f"{fmt_pl(l4['var_receiver'], 3)}; osobliwość: {l4['singular']}; kod zbieżności: "
            f"{l4['conv_code']}; ostrzeżenia R: {len(l4['r_warnings'])}; "
            f"czas {fmt_pl(l4['time_s'], 0)} s."
        )
    ec = br.get("estimator_check")
    if ec:
        L.append(
            f"- Kontrola estymatora (GPBoost vs lme4): β {fmt_pl(ec['beta_gpboost'], 4)} vs "
            f"{fmt_pl(ec['beta_lme4'], 4)}; wariancje nadawcy {fmt_pl(ec['var_sender'][0], 2)} vs "
            f"{fmt_pl(ec['var_sender'][1], 2)}, odbiorcy {fmt_pl(ec['var_receiver'][0], 3)} vs "
            f"{fmt_pl(ec['var_receiver'][1], 3)}; "
            + (
                "**rozbieżność: wrażliwy na estymator**."
                if ec["rozbieznosc"]
                else "brak rozbieżności."
            )
        )
    L.append(
        "\nUwaga: M2 i M1 mają inny estymand (efekt populacyjny vs warunkowy na efekty losowe), "
        "co przy dużej wariancji nadawcy tłumaczy różnice rzędu 0,01-0,05 w β.\n"
    )
    L.append("## 4. Pliki w `reports/h3a/export/`\n")
    L += [f"- `{f}`" for f in export_files] + [""]
    path = Path(report_dir) / "summary_level3.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path
