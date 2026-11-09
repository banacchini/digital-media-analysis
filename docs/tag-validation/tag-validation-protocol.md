# Walidacja tagów: protokół (przed zamrożeniem kontraktu danych v1)

**Decyzja zespołu (2026-11-09):** walidacja tagów odbywa się **przed** zamrożeniem v1. Plik `tag_category_proposal.csv` jest zamrożony; jego SHA-256 to
`1e5625c563ff65dac2a90d6ff4509ac19633b51669583c07ae2b4ab0a2f94ab8` (68 tagów kanonicznych). Wyniki walidacji **nie edytują** tego pliku: trafiają do nowych plików (`consensus_*.csv`, `tag_merge_decisions.csv`).
> **Wariant jednoosobowy:** jeśli walidację wykonuje jedna osoba, obowiązuje `tag-validation-single-annotator.md` (zastępuje sekcje 2–5 tego dokumentu).

**Prowadzi:** Michał (inżynier pipelinu). **Annotują:** Dominik, Jakub i Michał (każdy wszystkie pozycje).

## 1. Co jest walidowane

| Zadanie | Pozycje | Instrument (agent) | Wzorzec | Miara |
|---|---|---|---|---|
| **A** | 124 surowe ciągi (w tym 54 formy emoji) → tag kanoniczny lub „brak” | mapowanie raw → kanoniczny | konsensus 3 osób | zgodność ważona swipe'ami, κ |
| **B** | 68 tagów kanonicznych → hobby / lifestyle / status / unclear | `proposed_category_claude` (główna) i `..._gemini` | konsensus 3 osób | κ, AC1, zgodność ważona swipe'ami |
| **C** | klastry duplikatów i decyzje projektowe (D13, D15, `student`) | — | wspólna decyzja zespołu | bez κ (decyzje, nie pomiar) |

Dla B kolumna `proposed_linked_field` (mapa tag → pole strukturalne z D13) **nie** jest annotowana: to decyzja projektowa, rozpatrywana w zadaniu C i w analizie wrażliwości.

## 2. Zasady (żeby pomiar miał sens)

1. **Ślepota:** nikt nie widzi propozycji agentów, mapowań ani cudzych arkuszy przed zakończeniem annotacji. Arkusze B zostały wygenerowane **bez** kolumn z propozycjami (sprawdzone testem).
2. **Te same definicje co agent.** Wklej do arkuszy (zakładka „Instrukcja”) tekst z `docs/codebook.md`, część D, czyli ten, który dostali agenci. Robocza wersja w arkuszu to tylko orientacja. Jeśli definicje annotatorów różnią się od agentowych, mierzycie zgodność dwóch różnych zadań.
3. Każdy annotator dostaje **inną losową kolejność** (ziarno 20261109). Niezależnie, bez omawiania pozycji.
4. Pytania o definicje: do autora codebooka, bez omawiania konkretnych tagów.
5. **Zapisz regułę decyzyjną w `docs/tag-validation/prereg.md` i zacommituj zanim ktokolwiek zajrzy do etykiet** (sekcja 4).
6. Nie podawać żadnego κ w dokumentach przed domknięciem procedury.

## 3. Kroki

1. **Potwierdzenie hashu** zamrożonego pliku i definicji (10 min, cały zespół).
2. **Arkusze A** buduje agent (`tag-validation-agent-prompt.md`, zadania Z1–Z3). Arkusze B już są (`tagval_B_annotator_{A,B,C}.xlsx`).
3. **Annotacja B**, potem **A** (ok. 1–1,5 h na osobę łącznie). Każdy zwraca swój plik prowadzącemu.
4. **Skrypt metryk** (`tagval_metrics.py`) osobno dla A i B, z wagami użycia z agenta (`tag_usage_*.csv`):
   ```
   python tagval_metrics.py --annotators A=B_A.xlsx B=B_B.xlsx C=B_C.xlsx --key canonical_tag \
     --agent-file tag_category_proposal.csv --agent-key canonical_tag \
     --agent-cols proposed_category_claude proposed_category_gemini \
     --weights tag_usage_canonical.csv --weights-key canonical_tag --out-dir wyniki_B
   ```
   Dla A: `--key raw_tag`, plik agenta z kolumnami `raw_tag`, `canonical_tag` (mapowanie), wagi z `tag_usage_raw.csv`.
5. **Rozstrzygnięcia:** pozycje oznaczone `DO_ROZSTRZYGNIECIA` w `consensus.csv` (trzy różne odpowiedzi) rozstrzygacie wspólnie, wynik wpisujecie do `consensus_{A,B}.csv`. Dopiero po tym liczy się końcowe metryki agentów.
6. **Zadanie C** (wspólnie, 30–45 min), patrz sekcja 5.
7. **Reguła decyzyjna** (sekcja 4) i **analiza wpływu** (agent, zadanie Z5): przeliczenie H1 mapowaniem konsensusu.
8. Raport: `reports/tag-validation/` + wpis w `docs/ai-disclosure.md` + link w sekcji 10 notebooka H1.

## 4. Reguła decyzyjna (propozycja do zatwierdzenia i zapisania z góry)

- **A (raw → kanoniczny):** zgodność agent–konsensus **ważona liczbą swipe'ów** ≥ 95% → mapowanie agenta zostaje. Poniżej → podstawą v1 staje się mapowanie konsensusu.
- **B (kategorie):** κ agent–konsensus ≥ 0,70 (główny agent: Claude; Gemini informacyjnie) i zgodność ważona swipe'ami ≥ 95% → kategorie agenta zostają. Poniżej → kategorie konsensusu.
- **Sufit ludzi:** κ Fleissa trzech annotatorów ≥ 0,60. Jeśli niżej, podział lifestyle/hobby jest niejednoznaczny już dla ludzi i **nie jest mierzalny**. Wtedy traktujemy go jako decyzję projektową, raportujemy wrażliwość (H1 z podziałem agenta, z podziałem konsensusu i z uzupełnianiem pól tagami wyłączonym) i nie twierdzimy, że „walidacja potwierdziła" kategorie.
- **Zawsze** raportujemy analizę wpływu (agent vs konsensus), niezależnie od wyniku reguły.

## 5. Jak czytać metryki

- **Wagi.** Błąd w rzadkim tagu jest nieistotny dla H1, a błąd w częstym (np. `student`) może zmienić zainteresowania dla większości swipe'ów. Dlatego zgodność ważona swipe'ami jest decydująca.
- **κ przy 68 pozycjach.** CI (bootstrap po pozycjach, 90%) będą szerokie; kategorie mają bardzo nierówne liczności (hobby ≈ 34–37, lifestyle ≈ 25–27, unclear ≈ 5–6, status = 1). κ jest wrażliwe na przewagę kategorii, więc obok niego AC1 Gwet'a i surowa zgodność. Kategoria `status` ma jedną pozycję: oceniaj ją po macierzy pomyłek, nie po κ.
- **Sufit.** κ Fleissa trójki ludzi to górna granica tego, czego można oczekiwać od agenta.
- **Pozycje spornych modeli.** W zamrożonej propozycji 10 z 68 tagów to rozbieżności Claude–Gemini. Skrypt raportuje zgodność agenta osobno dla pozycji, w których modele się zgadzają i nie (lista pozycji jest w pliku propozycji; annotatorzy jej nie otwierają przed końcem annotacji). To prawdopodobne miejsca, gdzie błędy się koncentrują.
- Zgodność Claude–Gemini (58/68) nie jest walidacją, bo oba to modele z podobnymi błędami.

## 6. Zadanie C: wspólny przegląd

Opis i klastry kandydatów są w osobnym pliku `tag-validation-task-C.md`. **Otwierać dopiero po zakończeniu annotacji A i B przez wszystkich** (plik zawiera uwagi z propozycji agentów i naruszałby ślepotę).

## 7. Artefakty

`reports/tag-validation/`: `summary_A.json`, `summary_B.json`, `consensus_A.csv`, `consensus_B.csv`, `disagreements_*.csv`, `confusion_*.csv`, `tag_merge_decisions.csv`, `impact.md`. Wpis w `docs/ai-disclosure.md` (co zrobił agent, kto annotował). Link w sekcji 10 notebooka H1. W `prereg.md` hash zamrożonego pliku, ziarno arkuszy (20261109), reguła z sekcji 4.
