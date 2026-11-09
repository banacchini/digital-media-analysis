#!/usr/bin/env python3
"""Buduje ślepe arkusze annotacji (XLSX) dla walidacji tagów.

Zadanie B: canonical_tag -> kategoria (hobby/lifestyle/status/unclear)
Zadanie A: raw_tag -> tag kanoniczny (lub "brak")

Arkusze NIE zawierają propozycji agentów ani żadnych kolumn z propozycjami.
Kolejność pozycji jest losowa i inna dla każdego annotatora (ziarno zapisane).

Przykłady:
  python tagval_make_sheets.py --task B --items items_B.csv --key canonical_tag \
      --labels hobby lifestyle status unclear --out-dir out --seed 20261109
  python tagval_make_sheets.py --task A --items items_A.csv --key raw_tag \
      --labels-file canonical_labels.txt --extra-label brak --out-dir out --seed 20261109

items_*.csv: jedna kolumna z kluczem pozycji (inne kolumny są IGNOROWANE).
"""

import argparse
import random
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
YELLOW = PatternFill("solid", start_color="FFF9C4")
HEAD = PatternFill("solid", start_color="D9D9D9")

DEFS_B = [
    ("hobby", "aktywność lub zainteresowanie wykonywane w czasie wolnym"),
    (
        "lifestyle",
        "nawyk, usposobienie lub preferencja dotycząca codziennego życia "
        "i współdzielenia mieszkania",
    ),
    ("status", "status społeczny lub zawodowy (np. student)"),
    ("unclear", "nie da się przypisać do jednej z powyższych bez dodatkowej informacji"),
]


def build(task, items, key, labels, annot, seed, out_dir, round_name="", subset=None):
    """items = PEŁNA lista (id pozycji liczone z niej, stałe między rundami);
    subset = liczba pozycji losowanych do tej rundy (np. retest)."""
    ids = {k: f"{task.lower()}{i + 1:03d}" for i, k in enumerate(sorted(items))}
    rng = random.Random(f"{seed}-{annot}" + (f"-{round_name}" if round_name else ""))
    order = list(items)
    if subset:
        sub_rng = random.Random(f"{seed}-subset-{round_name}")
        order = sub_rng.sample(sorted(items), subset)
    rng.shuffle(order)

    wb = Workbook()
    ws = wb.active
    ws.title = "Adnotacje"
    header = ["item_id", key, "etykieta", "uwagi"]
    ws.append(header)
    for c in ws[1]:
        c.font = Font(name=FONT, bold=True)
        c.fill = HEAD
    for k in order:
        ws.append([ids[k], k, None, None])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=FONT)
        row[2].fill = YELLOW
        row[3].fill = YELLOW
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 50

    # lista rozwijana (limit pola formuły: wartości trzymamy w osobnym arkuszu)
    lw = wb.create_sheet("Dozwolone")
    lw["A1"] = "etykieta"
    lw["A1"].font = Font(name=FONT, bold=True)
    for i, lab in enumerate(labels, start=2):
        lw.cell(row=i, column=1, value=lab).font = Font(name=FONT)
    dv = DataValidation(
        type="list",
        formula1=f"=Dozwolone!$A$2:$A${len(labels) + 1}",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Niedozwolona wartość",
        error="Wybierz wartość z listy.",
    )
    ws.add_data_validation(dv)
    dv.add(f"C2:C{len(order) + 1}")

    ins = wb.create_sheet("Instrukcja", 0)
    lines = [
        (
            f"Walidacja tagów, zadanie {task}: annotator {annot}"
            + (f", runda: {round_name}" if round_name else ""),
            True,
        ),
        (
            "Zasady: pracuj sam, nie otwieraj arkuszy innych osób, "
            "nie zaglądaj do plików z propozycjami agentów ani do mapowań.",
            False,
        ),
        (
            "Wypełnij kolumnę „etykieta” (żółta) dla KAŻDEJ pozycji w arkuszu „Adnotacje”, "
            "wybierając wartość z listy. „uwagi” są opcjonalne.",
            False,
        ),
        (
            "Nie zmieniaj kolejności ani kolumn A:B. "
            "Nie edytuj zapisanych odpowiedzi po zakończeniu.",
            False,
        ),
        (
            (
                "RUNDA POWTÓRNA: nie zaglądaj do swoich poprzednich odpowiedzi "
                "ani do propozycji agentów. Oceń każdą pozycję od nowa.",
                True,
            )
            if round_name
            else ("", False)
        ),
        (
            "W razie wątpliwości co do definicji pytaj autora codebooka. "
            "Nie omawiaj konkretnych pozycji z pozostałymi annotatorami do końca annotacji.",
            False,
        ),
    ]
    if task == "B":
        lines.append(
            (
                "Definicje kategorii: WKLEJ tu tekst z docs/codebook.md, część D "
                "(ten sam, który dostali agenci). "
                "Robocza wersja poniżej służy tylko do zorientowania się:",
                True,
            )
        )
        for lab, d in DEFS_B:
            lines.append((f"  {lab}: {d}", False))
    else:
        lines.append(
            (
                "Zadanie: dla każdego surowego ciągu wybierz tag kanoniczny, "
                "który oznacza to samo, albo „brak”, jeśli żaden nie pasuje.",
                False,
            )
        )
    lines.append(("Przykład wypełnionego wiersza (tylko format, nie z danych):", True))
    lines = [ln for ln in lines if ln[0]]
    ins_row = len(lines) + 1
    for i, (t, bold) in enumerate(lines, start=1):
        ins.cell(row=i, column=1, value=t).font = Font(name=FONT, bold=bold)
        ins.cell(row=i, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    example = ["x000", "przykładowa_pozycja", labels[0], "opcjonalna uwaga"]
    for j, v in enumerate(example, start=1):
        ins.cell(row=ins_row, column=j, value=v).font = Font(name=FONT, italic=True)
    ins.column_dimensions["A"].width = 120
    ins.column_dimensions["B"].width = 26
    ins.column_dimensions["C"].width = 16
    ins.column_dimensions["D"].width = 22

    suffix = f"_{round_name}" if round_name else ""
    path = Path(out_dir) / f"tagval_{task}_annotator_{annot}{suffix}.xlsx"
    wb.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["A", "B"])
    ap.add_argument("--items", required=True)
    ap.add_argument("--key", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--labels", nargs="+")
    g.add_argument("--labels-file")
    ap.add_argument("--extra-label", nargs="*", default=[])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--annotators", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--round", default="", help="nazwa rundy, np. retest")
    ap.add_argument(
        "--subset", type=int, default=None, help="losuj tyle pozycji do tej rundy (np. retest)"
    )
    a = ap.parse_args()

    items = pd.read_csv(a.items)[a.key].dropna().astype(str).str.strip()
    items = sorted(set(items))
    labels = a.labels or [
        ln.strip()
        for ln in Path(a.labels_file).read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    labels = list(dict.fromkeys(labels + a.extra_label))
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for annot in a.annotators:
        p = build(a.task, items, a.key, labels, annot, a.seed, a.out_dir, a.round, a.subset)
        print(f"zapisano {p.name}")
    print(f"pozycji: {len(items)}, etykiet: {len(labels)}")


if __name__ == "__main__":
    sys.exit(main())
