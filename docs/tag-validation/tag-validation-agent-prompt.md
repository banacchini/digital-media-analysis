# Prompt: walidacja tagów, część agentowa (arkusze A, wagi użycia, analiza wpływu)

## Rola i kontekst

Pracujesz w repo projektu RentFriends (kurs AMC, PWr). Zespół waliduje normalizację i klasyfikację tagów **przed** zamrożeniem kontraktu danych v1 (protokół: `docs/tag-validation/tag-validation-protocol.md`, metryki: `scripts/tagval_metrics.py`, generator arkuszy: `scripts/tagval_make_sheets.py`; skopiuj te pliki do repo, jeśli ich jeszcze nie ma). Ludzie annotują **ślepo**; Twoje zadania to przygotowanie materiałów i, po zakończeniu annotacji, analiza wpływu.

Gałąź `feat/tag-validation`. Nie modyfikuj `rentfriends.h1`, `rentfriends.h2`, `rentfriends.h3a`, `rentfriends.graph`, `rentfriends.h3b`.

## Zasady nadrzędne

1. **Pliki zamrożone, nie edytować, nie nadpisywać:** `docs/tag_category_proposal.csv` (SHA-256 musi być `1e5625c563ff65dac2a90d6ff4509ac19633b51669583c07ae2b4ab0a2f94ab8`), `docs/interests_mapping.csv`, `h1_analysis_dataset.parquet` (kontrakt danych). Sprawdź hash propozycji na starcie; jeśli się różni, **zatrzymaj się** i napisz o tym (wypisz tylko „zgodny/niezgodny").
2. **Ślepota ludzi.** Mapowania raw → kanoniczny, propozycji agentów i ich notatek **nie wypisuj** na terminal ani do logów (człowiek uruchamiający Cię jest annotatorem). Wypisuj wyłącznie liczby i nazwy kolumn. Arkusze dla annotatorów nie mogą zawierać żadnej kolumny z mapowaniem ani propozycją.
3. **Środowisko:** wyłącznie `uv run --frozen`. **Nigdy** `uv run --active`. Nie zmieniaj `uv.lock`, nie dotykaj `~/.venv` ani niczego poza katalogiem repo; jeśli brakuje pakietu (np. `openpyxl`), zapisz to w `docs/tag-validation/open-questions.md`.
4. Tagi nie są danymi osobowymi, ale **bio nie czytasz, nie wyświetlasz ani nie przetwarzasz** w tym zadaniu. Brak `user_key` w wynikach (tylko agregaty).
5. Małe opisowe commity (jeden krok = jeden commit), bez squashowania. Testy i lintery (`ruff`, `pytest`) przed commitem. Deterministycznie (ziarno 20261109 dla arkuszy, 42 dla reszty).
6. Niejednoznaczne decyzje: `docs/tag-validation/open-questions.md`, wybierz wariant konserwatywny z adnotacją.

## Zadania (Z1–Z4 teraz; Z5 dopiero po konsensusie ludzi)

**Z1. Weryfikacja stanu.** Sprawdź hash propozycji (zasada 1). Wypisz liczby: tagów kanonicznych w propozycji (oczekiwane 68), wierszy w `interests_mapping.csv`, unikalnych kanonicznych w mapowaniu (oczekiwane 67), unikalnych surowych ciągów (oczekiwane 124, w tym 54 emoji). **Rozbieżności wypisz liczbami i zapisz w `open-questions.md`**, nie „naprawiaj" ich.

**Z2. Pozycje zadania A.** Zbierz **wszystkie unikalne surowe ciągi tagów** występujące w danych użytkowników (profile i historia, w próbie H1 lub szerzej, ale spójnie z mapowaniem), zapisz jako `data/tagval/items_A.csv` z jedyną kolumną `raw_tag` (bez kanonicznych odpowiedników). Wypisz liczbę ciągów i ile z nich ma wpis w mapowaniu. Jeśli jakieś nie mają wpisu, zapisz ich liczbę w `open-questions.md` i **dołącz je do items_A** (annotatorzy mają je również ocenić; agent oznaczył je jako „brak" lub pominął, co też jest wynikiem).

**Z3. Arkusze zadania A.** Uruchom generator:
```
uv run --frozen python scripts/tagval_make_sheets.py --task A --items data/tagval/items_A.csv \
  --key raw_tag --labels-file data/tagval/canonical_labels.txt --extra-label brak \
  --out-dir data/tagval/sheets_A --seed 20261109
```
gdzie `canonical_labels.txt` to 68 tagów kanonicznych **z zamrożonej propozycji** (jedna etykieta na linię, bez żadnych innych informacji). Napisz test: arkusze nie zawierają kolumn poza `item_id`, `raw_tag`, `etykieta`, `uwagi` ani żadnych napisów z kanonicznym odpowiednikiem w kolumnie klucza; zbiory pozycji identyczne dla A, B, C; kolejności różne. Annotatorzy A, B, C dostaną po jednym pliku (w wariancie jednoosobowym użyj `--annotators A`; do rundy powtórnej patrz `tag-validation-single-annotator.md`).
Plik agenta dla metryk: `data/tagval/agent_A.csv` z kolumnami `raw_tag`, `canonical_tag` (mapowanie agenta; **nie wyświetlaj**; dla surowych bez wpisu: `brak`).

**Z4. Wagi użycia.** Dla próby H1 (92 754 swipe'ów, te same reguły as-of co w H1) policz:
- `data/tagval/tag_usage_raw.csv`: `raw_tag`, `n_profiles`, `n_swipes` (liczba swipe'ów, w których tag występuje na profilu nadawcy lub odbiorcy),
- `data/tagval/tag_usage_canonical.csv`: `canonical_tag`, `n_profiles`, `n_swipes` (po mapowaniu agenta).
Używaj tych samych funkcji co budowa zbioru H1 (importuj tylko do odczytu); jeśli tagi stylu życia nie są w zbiorze H1, policz je z tego samego źródła as-of. Wypisz tylko sumy kontrolne (liczby wierszy i suma `n_swipes`).

**Z5. Analiza wpływu (uruchom dopiero, gdy istnieją `data/tagval/consensus_A.csv` i `consensus_B.csv` z rozstrzygnięciami ludzi).**
- Nowy moduł `src/rentfriends/h1_tagval.py` (nie modyfikuj `h1.py` ani `dataset_h1.py`): wersja budowy cech H1 z parametrami `raw_to_canonical_override` (z `consensus_A.csv`) i `category_override` (z `consensus_B.csv`). Wyjście do **osobnego** pliku `data/processed/h1_analysis_dataset_consensus.parquet`; kontrakt danych nietknięty (sprawdź sumę kontrolną przed i po).
- Scenariusze: (i) mapowanie agenta (baseline), (ii) konsensus A+B, (iii) konsensus tylko A, (iv) konsensus tylko B, (v) agent bez uzupełniania pól stylu życia tagami (D13 wyłączone).
- Dla każdego: n próby; odsetek swipe'ów, w których zmienił się zbiór zainteresowań lub którekolwiek pole stylu życia, względem baseline; średnie ΔLL bloków po 6 kolejnościach (wiek / zainteresowania / styl życia) z tą samą specyfikacją co w głównej analizie H1 (pooled logit, te same kontrole); średni Jaccard prawych i lewych; kierunek i wielkość zmiany.
- Odpowiedz na jedno pytanie w `reports/tag-validation/impact.md`: **czy wniosek H1 (wiek dominuje, styl życia słaby, zainteresowania najsłabsze) zmienia się przy mapowaniu konsensusu?** Raportuj liczby, nie interpretacje bez liczb. Jeśli wniosek się zmienia, napisz jak, bez zmiany dotychczasowego tekstu H1 (to decyzja zespołu).

## Dostarczane artefakty

1. `data/tagval/items_A.csv`, `sheets_A/` (3 arkusze), `agent_A.csv`, `tag_usage_raw.csv`, `tag_usage_canonical.csv` (git-ignored, jeśli zespół woli; `docs/tag-validation/` śledzone).
2. Testy: ślepota arkuszy, zgodność hashy, deterministyczność, sumy kontrolne wag.
3. (Po konsensusie) `h1_tagval.py`, plik `h1_analysis_dataset_consensus.parquet`, `reports/tag-validation/impact.md` i `impact.json`.
4. `docs/tag-validation/open-questions.md` oraz wpis w `docs/ai-disclosure.md` (co wykonał agent; incydenty środowiskowe, jeśli wystąpiły).

## Kryteria akceptacji

- Hash zamrożonej propozycji i suma kontrolna kontraktu danych niezmienione.
- Arkusze A nie zawierają żadnych informacji o mapowaniu agenta; logi nie zawierają mapowań ani propozycji.
- Wagi użycia zsumowane i zgodne ze zbiorem H1 (liczba swipe'ów 92 754).
- Brak zmian w `uv.lock`; brak `uv run --active`.
- W analizie wpływu każde zdanie wniosku ma liczbę w `impact.json`.
