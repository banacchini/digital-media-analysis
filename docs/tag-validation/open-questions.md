# Walidacja tagów: otwarte kwestie (agent, Z1–Z4)

Data: 2026-11-09. Same liczby i nazwy kolumn; żadnych mapowań ani propozycji (ślepota annotatora).
Odtworzenie: `uv run --frozen python -m rentfriends.tagval_prep` (kod: `src/rentfriends/tagval_prep.py`).

## Stan (Z1)

Hash `docs/tag_category_proposal.csv`: zgodny. Hash propozycji, `interests_mapping.csv` i `h1_analysis_dataset.parquet` przed i po uruchomieniu: bez zmian.

| Wielkość | Oczekiwane | Jest |
|---|---|---|
| tagi kanoniczne w propozycji | 68 | 68 |
| wiersze w `interests_mapping.csv` | n/d | 124 |
| unikalne kanoniczne w mapowaniu | 67 | 67 |
| unikalne surowe w mapowaniu | 124 | 124 |
| z tego formy z emoji (znak Unicode `So`) | 54 | **53** |

## Rozbieżności i decyzje

| # | Rozbieżność | Co zrobiono (wariant konserwatywny) |
|---|---|---|
| Q1 | Słownik kanoniczny mapowania i propozycji się nie pokrywa: 1 kanoniczny z mapowania nie ma wpisu w propozycji (dotyczy 3 surowych ciągów), 2 tagi z propozycji nie mają żadnego wiersza w mapowaniu (0 swipe'ów w próbie H1). | Niczego nie „naprawiano". Etykiety arkusza = 68 tagów z zamrożonej propozycji + `brak`. Dla tych 3 ciągów mapowanie agenta wskazuje etykietę spoza listy annotatora, więc zgodność agenta z konsensusem nie może tu zajść (chyba że konsensus = „brak"). Do uwzględnienia przy czytaniu wyniku A. |
| Q2 | Emoji: 53 w mapowaniu zamiast oczekiwanych 54. Kryterium „emoji" = ciąg zawiera znak o kategorii Unicode `So`; w danych to zawsze emoji **plus** tekst (żaden ciąg nie składa się z samych piktogramów). Przy innej definicji liczba może wynosić 54. | Brak działania; wartość 54 w protokole należy zweryfikować u autora. |
| Q3 | Surowe ciągi poza mapowaniem: 4 (`profile_history` ma 128 unikalnych surowych, `users` 124). Wszystkie 4 występują tylko w historii i wszystkie 4 zawierają piktogram. | Dołączone do `items_A.csv` (128 pozycji); w `agent_A.csv` mają `brak`. Uwaga: potok H1 nie oznacza ich jako „brak", tylko przepuszcza surowy ciąg jako własny tag kanoniczny (`mapping.get(tag, tag)`). Wagi kanoniczne liczą je pod `brak` (38 swipe'ów). |
| Q4 | Próba H1 = 92 754 swipe'ów to zbiór po `prepare_h1_sample` (specyfikacja domyślna) z 94 295 wierszy kontraktu; nie sam kontrakt. | Plik kontraktu czytany bezpośrednio (`pd.read_parquet`), bez `load_h1_data`, bo ta funkcja przebudowałaby i nadpisała kontrakt przy zmianie kolumn. |
| Q5 | Definicje wag nie były jednoznaczne w poleceniu. | `n_swipes` = swipe liczony raz, gdy tag jest na profilu nadawcy lub odbiorcy (profil as-of, te same reguły D7 co w H1). `n_profiles` = unikalni użytkownicy z tym tagiem w którymkolwiek swipe'ie próby (jako nadawca lub odbiorca). Tagi stylu życia liczone z surowych `interests` tym samym źródłem as-of (zbiór H1 ich nie zawiera). |
| Q6 | Sumy wag nie równają się 92 754, bo swipe ma wiele tagów. | Kontrola: wiersze i sumy `n_swipes` (raw: 128 wierszy, 1 259 223; kanoniczne: 68 wierszy, 1 248 460) oraz maksimum ≤ 92 754 (raw 79 768, kanoniczne 79 966). 6 swipe'ów nie ma żadnego tagu po żadnej stronie. |
| Q7 | Kolejność etykiet w liście rozwijanej. | `canonical_labels.txt` posortowany alfabetycznie, nie w kolejności propozycji (kolejność mogłaby zdradzać grupowanie kategorii). Generator dodaje `brak` (razem 69 opcji). |

## Środowisko i git

- Praca jest na gałęzi `fix/h1-audit`, nie na `feat/tag-validation` jak w poleceniu. **Nic nie zacommitowano** (`AGENTS.md`, zasada 6: agent nie commituje bez prośby).
- `.gitignore` zawiera teraz `!data/tagval/**` (zmiana spoza tej sesji), więc `data/tagval/agent_A.csv` (mapowanie agenta) jest widoczny dla gita jako plik nieśledzony. Hook `block-data-files` zatrzyma commit, ale nie `git add`. Przed pracą annotatora nie dodawać tego pliku do indeksu.
- Każde `uv run --frozen` wypisuje ostrzeżenie o `VIRTUAL_ENV=/home/dominik/.venv`; zignorowane, `--active` nie użyto. `uv.lock` i `pyproject.toml` (dodane `openpyxl`) miały zmiany sprzed tej sesji; nie dotykano.
- `ruff check .` zgłasza uwagi tylko w dostarczonych `scripts/tagval_*.py` (nie zmieniane). `pytest`: 3 błędy w `tests/test_eda.py` (brak pliku metadanych), niezwiązane z tym zadaniem.

## Z5: analiza wpływu (scenariusze i–vi)

Wyniki: `reports/tag-validation/impact.md` i `impact.json`. Kod: `src/rentfriends/h1_tagval.py`. Dane wyjściowe: `data/processed/h1_analysis_dataset_consensus.parquet` (ii) i `..._consensus_merged.parquet` (vi); kontrakt danych nietknięty (hash przed i po).

| # | Kwestia | Co zrobiono (wariant konserwatywny) |
|---|---|---|
| Q8 | Polecenie zakłada, że scalenie `going_out_friends → often_out` zmienia pole D13 z „brak” na `lifestyle`. W kodzie `TAG_TO_STRUCTURED_FIELD_MAP` nie ma ani `often_out`, ani `going_out_friends`, a `proposed_linked_field` jest wczytywane, ale zbiór H1 go nie używa. Kody pola `lifestyle` (S/M/W) nie mają znaczenia w codebooku. | Scenariusz (vi) używa mapy D13 z kodu: skutek uzupełniania tego scalenia wynosi 0 (zmiana statusu pola `lifestyle` w 0 swipe'ów). Efekt „co by było” policzono osobno w dwóch scenariuszach diagnostycznych z kodem zastępczym `OUT`; to założenie, nie dane. Decyzja, czy i jakim kodem uzupełniać `lifestyle`, wymaga ustalenia znaczenia kodów. |
| Q9 | Scalenie `peace_and_quite → likes_calm` wprowadza posiadaczy `peace_and_quite` do grupy ciszy D15 (tag nie był w grupie, cel jest). | Zgłoszone w `impact.md`. Skutek na konflikty D15: 0 swipe'ów (przybywa 0, ubywa 0); zmienia się liczba wspólnych tagów stylu życia (rośnie w 9 054, maleje w 397 swipe'ach). Pary polaryzacji przemapowane bez utraty konfliktów. |
| Q10 | Odsetek swipe'ów z konfliktem D15 w kontrakcie wynosi 51,7% (wszystkie wiersze). Nie sprawdzano przyczyny; wydaje się wysoki jak na cztery pary kierunkowe. | Bez działania (poza zakresem). Do sprawdzenia przed v1: które grupy generują konflikty. |
| Q11 | `consensus_A` z `konsensus = brak` nie jest nadpisaniem (zostaje baseline); takich wierszy w danych jest 0. Nadpisań A jest 8 (m.in. poprawka `business` → `bussiness` w 3 ciągach). | Brak działania. |
| Q12 | Przedziały ufności dla różnic między scenariuszami nie były liczone. | Raportowane różnice punktowe na tej samej próbie, z zastrzeżeniem w raporcie. |
