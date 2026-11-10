# H2: naprawa po audycie (2026-11-10)

Gałąź `fix/h2-audit`, prompt `docs/prompts/fix-h2-prompt-v2.md`. Zakres tej sesji uzgodniony z autorem
prompta: **P1 + P2 (Z1, Z2, Z3, Z4, Z7) i dokumentacja**. **Pominięte na polecenie:** formalne odtworzenie
liczb sprzed zmian (zasada 3) i cały P3 (Z5 wrażliwość, Z6 `y_match`); zob. `open-questions.md`.

H2 pozostaje **eksploracyjne** (macierz płci widziano przed sformułowaniem hipotezy, D17). Wszystkie OR
poniżej mają podany estymator: **pooled** = regresja logistyczna, SE klastrowane po nadawcy i odbiorcy
(OR populacyjne); **GLMM** = crossed random intercepts nadawcy i odbiorcy (OR warunkowe), SE z `lme4`
(`glmer`, nAGQ = 0) albo z GPBoost, gdy ten je zwrócił; źródło jest zapisane przy każdym modelu.

## Kontrola liczb sprzed zmian (nie jako bramka)

Zgodnie z poleceniem nie zatrzymywałem się na odtworzeniu liczb. Funkcje sprzed audytu
(`h2.rate_matrix`, `or_by_sender_sex`, `grouped_cv`) są niezmienione i notebook wywołuje je na tych samych
danych. Wartości z notebooka zgadzają się z tymi z promptu (tolerancja po zaokrągleniu): macierz stawek
F→F 0,200, F→M 0,085, M→F 0,296, M→M 0,199; OR surowy F 2,645, M 0,602; OR z kontrolami F 2,439, M 0,657;
AUC w CV (średnia z foldów po nadawcach) płeć 0,603, płeć + wiek 0,620. To nie zastępuje formalnego testu, tylko
potwierdza, że punkt wyjścia się nie zmienił.

## Tabela: problem → ustalenie → zmiana → liczby przed → po

| # | Problem (audyt) | Ustalenie | Zmiana | Przed | Po | Status |
|---|---|---|---|---|---|---|
| Z1 | „Z tych danych nie umiemy rozdzielić popularności profili kobiet i premii za własną płeć" | **Częściowo rozdzielić się da, ale tylko przy założeniu.** W tabeli 2×2 z efektami nadawcy i odbiorcy identyfikowany jest jeden kontrast (iloraz luk „odbiorca F vs M" u nadawców F i M, `exp(2h)`). `π` i `h` wymagają założenia, że popularność i premia są takie same dla obu płci nadawców. Rachunek orientacyjny z promptu (0,76 i 0,22 logitu) **potwierdzony**: `π` = 0,757, `h` = 0,233 (pooled) | `h2_audit.z1_*`: model `sender_F(±1) × receiver_F`; kodowania `refF`/`refM` dla CI luk; model z FE nadawcy; płeć `O` poza modelem (G16) | brak liczby; OR surowy F 2,65, M 0,60 mieszały oba efekty | pooled: `π` OR 2,13 [1,81; 2,51], `h` OR 1,26 [1,08; 1,48], `exp(2h)` 1,59 [1,16; 2,18]. GLMM (lme4): `π` 3,91 [3,47; 4,39], `h` 1,39 [1,32; 1,47], `exp(2h)` 1,93 [1,73; 2,16]. Z kontrolami (wiek, miasto), pooled: `π` 1,91 [1,63; 2,25], `h` 1,25 [1,07; 1,47] | post hoc (audyt) |
| Z1b | Efekty stałe nadawcy | Wewnątrz nadawcy (SE po odbiorcy): `receiver_F` OR 3,19 (log 1,159, SE 0,056); z interakcją `receiver_F` 1,21 i `sender_F:receiver_F` 0,34 (log, SE 0,058 i 0,033) | `h2_audit.z1_fixed_effects` | brak | kierunek jak w modelu głównym; OR najbardziej warunkowe, tylko kontrola kierunku | post hoc (audyt) |
| Z2 | Brak efektu wieku (tylko kontrola i CV) | Dodano macierz 4×4 i model `same_band`, `age_band_diff_abs`, `age_band_diff` (karta M1: `\|Δwiek\|`, `Δwiek`) z FE pasma nadawcy jako wrażliwością | `h2_audit.age_matrix`, `age_design`, `z2_models` (parametryzacja `linear` i równoważna `dir`, ten sam log-likelihood) | brak | OR starszego odbiorcy na pasmo: pooled FE 0,69 [0,61; 0,77], bez FE 0,58 [0,47; 0,72], GLMM 0,49 [0,44; 0,53]. Młodszy: pooled 0,96 [0,86; 1,07], GLMM 0,92 [0,84; 1,01]. To samo pasmo: pooled 1,03 [0,90; 1,17], GLMM 1,00 [0,89; 1,11] | specyfikacja **pre-rejestrowana** (karta M1); FE pasma, macierz i `dir` post hoc (audyt) |
| Z2b | Spójność z H1 (OR starszego o 1 pasmo 0,62 [0,57; 0,68] itd.) | Odtworzone `age_direction_check` na próbie H1 (92 754). **Różnica wynika z kontroli płci i miasta, nie z próby (93 717 vs 92 754) ani z klastrowania** | `h2_audit.h1_bridge`: jedna zmiana naraz | starszy o 1: 0,62 [0,57; 0,68]; o 2+: 0,36 [0,29; 0,43]; młodszy o 1: 0,97 [0,87; 1,09] | próba H2: 0,62 [0,57; 0,68] / 0,35 [0,29; 0,43] / 0,97 [0,87; 1,09]; + klastry nadawca i odbiorca: 0,62 [0,55; 0,70] / 0,35 [0,29; 0,44] / 0,97 [0,86; 1,10]; + kontrole: **0,67 [0,59; 0,74] / 0,41 [0,33; 0,50] / 0,92 [0,82; 1,04]** | post hoc (audyt) |
| Z3 | Estymator niezgodny z D18 (tylko pooled) | GPBoost zbiega, ale w większości modeli nie zwraca SE (jak w D-H3a-26); w Z1 z kontrolami zwrócił. Gdzie nie zwrócił, SE z `lme4`. Wariancja efektu nadawcy 7,5 (lme4) / 7,9 (GPBoost) | `h2_audit.estimate`: zawsze pooled i GLMM, `glmm_source`, `primary` (GLMM albo fallback pooled) | OR tylko pooled | tabela obok siebie w notebooku 6.1: GLMM jest dalej od 1 (np. `π` 2,13 vs 3,91; starszy 0,69 vs 0,49). **GLMM ma za wąskie CI dla efektów zależnych od nadawcy** (brak losowych nachyleń; `h`: [1,32; 1,47] vs pooled [1,08; 1,48]) | post hoc (audyt); wybór estymatora głównego nadal otwarty (Q2) |
| Z4a | Brak AUC-PR | Dodane | `h2_audit.cv_summary` | AUC, log loss | AUC-PR płeć + wiek 0,29 [0,25; 0,33] przy odsetku bazowym 0,21 | post hoc (audyt) |
| Z4b | Przeciek po odbiorcach | CV grupowane po odbiorcach jako drugi widok | `cv_oof(group="receiver")` | tylko foldy po nadawcach | nowy odbiorca: AUC płeć 0,61 [0,59; 0,64], płeć + wiek 0,64 [0,61; 0,67] | post hoc (audyt); foldy po nadawcach były D18 |
| Z4c | Odchylenie między foldami zamiast CI | Sparowany bootstrap po nadawcach na predykcjach out-of-fold (1000 powtórzeń, ten sam resampling dla obu modeli) | `cv_summary` | wiek: Δ log loss −0,003, „w szumie" (rozrzut 0,004) | wiek dodaje do płci (blok `sex+age3`, nowy nadawca): Δ log loss −0,0045 [−0,0078; −0,0010], ΔAUC +0,035 [0,018; 0,053], ΔAUC-PR +0,033 [0,020; 0,048]. Stary blok `sex+age`: Δ log loss −0,0034 [−0,0066; −0,0003]. **Wniosek o wieku się zmienia: drobny, ale ponad szum** | post hoc (audyt) |
| Z4d | Model null w CV | Zbiorcze OOF z różnymi stałymi w foldach daje sztuczne AUC ≠ 0,5 (w pierwszej wersji kodu 0,445, wykryte i naprawione przed wynikami) | null przewiduje jedną stałą: AUC = 0,5, AUC-PR = odsetek bazowy | — | log loss null 0,5089 | naprawa błędu własnego kodu |
| Z4e | Blok wieku | Dodany blok `sex+age3` (o `age_band_diff_abs`), zgodny z H1; stary `sex+age` zostaje obok | `cv_design` | `sex+age` | oba bloki raportowane | post hoc (audyt) |
| Z7 | Sekcja 7 | Przepisana: wynik Z1 z założeniem identyfikacyjnym, korelacja a nie preferencja, ekspozycja (G1); usunięta „Czego nie oszacowaliśmy" dla wieku; nagłówek spójny z H1; efekty w p.p. i OR z estymatorem; podział konfirmacyjne/eksploracyjne/post hoc; ograniczenia | `notebooks/h2_demographics.ipynb`, `docs/h2/h2-summary.md` | — | — | — |
| — | Cache | Ciężkie obliczenia w `data/interim/h2/` (poza gitem), klucz = hasz danych + parametry + `CODE_VERSION`; wykresy w `h2_figs` tylko czytają `R` | `h2_cache.py`, `h2_figs.py` | notebook liczył wszystko za każdym razem | pierwszy przebieg od zera ok. 20 min, kolejne kilka sekund | — |

## Czego nie zrobiono

- **Z5 (wrażliwość rozszerzona)** i **Z6 (`y_match`)**: poza zakresem na polecenie. Zostają w pliku
  `open-questions.md`. Sześć scenariuszy wrażliwości sprzed audytu zostaje (notebook 6.2) bez zmian.
- Formalne odtworzenie liczb sprzed zmian jako warunek rozpoczęcia pracy (zob. wyżej).

## Ujawnienie użycia AI

Narzędzie: Claude Code (Claude Sonnet 5.5), sesja 2026-11-10, polecenia wydane przez Dominika (banacchini).
Wygenerowane przez AI: `src/rentfriends/h2_cache.py`, `h2_audit.py`, `h2_figs.py`, `tests/test_h2_audit.py`,
notebook `notebooks/h2_demographics.ipynb` (komórki i tekst sekcji 7), te dokumenty. Zweryfikowane
(przez agenta, nie przez człowieka): testy jednostkowe na danych symulowanych, zgodność liczb z tekstem
sekcji 7 (porównanie z tabelą „Liczby do wniosku"), rysunki obejrzane jako obrazy. **Niezweryfikowane
przez człowieka:** interpretacja założenia identyfikacyjnego i sformułowania sekcji 7.

Incydenty i odstępstwa w tej sesji:

1. **Pominięcie zasady 3 i P3 na polecenie autora** (wyżej).
2. **Pierwszy przebieg obliczeń zatrzymany po PID i powtórzony.** GPBoost nie zwracał SE, więc po
   zobaczeniu pierwszego wyniku dodałem `lme4` jako źródło SE i podniosłem `CODE_VERSION`. Zatrzymałem
   tylko własny proces (po PID), bez `pkill`; cache z pierwszego przebiegu został unieważniony.
3. **Zmiana estymatora po zobaczeniu wyniku (SE GPBoost).** Nie zmieniła specyfikacji modeli ani wyników
   punktowych, tylko źródło SE; opisane tu i w `open-questions.md` (Q2), bo D-H3a-26 zastrzegało decyzję o `lme4`
   dla Dominika. Prompt pozwalał importować opakowania GLMM i cross-check `lme4`; użycie `lme4` jako źródła SE (a nie tylko kontroli) to rozszerzenie jego roli i wymaga potwierdzenia.
4. **Błąd własnego kodu wykryty przed wynikami:** AUC modelu null w zbiorczym OOF (zob. Z4d).
5. **Błąd narzędzia bez skutku:** pierwszy zapis pliku `h2_cache.py` użył niepoprawnych nazw parametrów
   narzędzia, ale został przyjęty; kod w repo nie był tym dotknięty.
6. Dane: `bio` nie było wczytywane; do `lme4` trafiają całkowite kody nadawców i odbiorców w prywatnym katalogu
   tymczasowym (usuwanym po fitcie), bez `user_key`. W repo nie ma wierszy tabel ani `user_key`.
7. Środowisko: tylko `uv run --frozen`; bez `--active` i `pkill`; `uv.lock` i `pyproject.toml` bez zmian.
