# D15: skąd 52% swipe'ów z konfliktem tagów stylu życia? (Z1, 2026-11-09)

Gałąź `fix/h1-rebase-v1`. Kod: `src/rentfriends/h1_d15.py`, `scripts/d15_investigation.py`, testy `tests/test_h1_d15.py`.
Agregaty: `reports/h1/d15_prevalence.json` (bez kluczy użytkowników i bez `bio`). Próba H1: n = 92 754 (kompletne przypadki głównej specyfikacji).

## Wniosek

**To jest prawdziwa prewalencja, nie błąd implementacji. Kod zmiennej nie został zmieniony, więc nie ma skutku „przed/po poprawce" na H1.**
Obserwowany odsetek konfliktów jest równy odsetkowi oczekiwanemu, gdyby nadawca i odbiorca mieli tagi niezależnie od siebie (permutacja tagów odbiorców, 200 powtórzeń, ziarno 42):

| | konflikt obserwowany | konflikt przy niezależności stron [95% pasmo permutacji] |
|---|---|---|
| v0, próba H1 | 52,32% | 52,39% [52,16; 52,60] |
| v1 (kandydat (vi)), próba H1 | 52,41% | 52,51% [52,27; 52,73] |

(Wszystkie 94 295 swipe'ów po wykluczeniu Hyderabadu: 51,72% w v0 i 51,81% w v1; „51,7–52,4%" z promptu to ten sam zakres, zależnie od próby.)

## Definicja i zgodność z codebookiem

`compute_lifestyle_tag_conflict` (`dataset_h1.py`) zwraca 1, gdy w którejś grupie z `POLARITY_PAIRS` jedna strona ma tag ze strony `pos`, a druga ze strony `neg` (w dowolnym kierunku). Codebook (część C): „1 if the pair has conflicting tags in a `polarity_group`; 0 where one side lacks the group". Kod robi dokładnie to. Sprawdzone i wyklucza błąd: brak tagu nie daje konfliktu (konflikt wśród swipe'ów, gdzie którakolwiek strona nie ma żadnego tagu stylu życia: 0,0%), obie strony tej samej strony grupy nie dają konfliktu, strony nie są zamienione (wynik symetryczny), a ponowne policzenie z zapisanych zbiorów tagów daje identyczną kolumnę (zgodność 100%).

**Uwaga do promptu:** w kodzie jest **pięć** grup polaryzacji, nie cztery: (0) `smoker` vs `non_smoker`; (1) `early_bird` vs `night_owl`; (2) `extrovert` vs `introvert`; (3) `no_pets` vs `animals`, `cat_person`, `dog_person`; (4) `likes_calm`, `quiet_evenings`, `silence_after_22`, `chill_at_home`, `mostly_home` vs `likes_parties`, `music_nonstop`.

## Rozkład po grupach (próba H1, v0)

| Grupa | konflikt | niezależność [pasmo] | nadawca ma tag grupy | odbiorca ma tag grupy | któraś strona | obie strony |
|---|---|---|---|---|---|---|
| 0 palenie | 17,18% (15 931) | 17,47% [17,29; 17,67] | 63,8% | 62,1% | 86,1% | 39,8% |
| 1 pora dnia | 4,38% (4 062) | 4,50% [4,40; 4,60] | 34,4% | 35,4% | 57,6% | 12,1% |
| 2 ekstrawersja | 13,85% (12 844) | 13,87% [13,65; 14,03] | 51,6% | 52,8% | 77,2% | 27,2% |
| 3 zwierzęta | 6,41% (5 945) | 6,31% [6,18; 6,44] | 43,5% | 44,4% | 68,4% | 19,4% |
| 4 spokój vs imprezy | 27,58% (25 579) | 27,59% [27,39; 27,75] | 68,5% | 66,7% | 89,6% | 45,6% |
| **dowolna grupa** | **52,32% (48 529)** | **52,39% [52,16; 52,60]** | 96,5% | 96,6% | 99,9% | 93,3% |

Liczba grup w konflikcie na swipe: 0 grup 44 225; 1 grupa 34 979; 2 grupy 11 420; 3 grupy 1 979; 4 grupy 150; 5 grup 1.

## Dlaczego tak dużo

- Tagi stylu życia są bardzo częste: 98,1% nadawców i 98,3% odbiorców ma co najmniej jeden (próba H1). Częste są zwłaszcza `non_smoker` (45% swipe'ów po stronie nadawcy), `extrovert` (31%), `likes_calm` (30%), `night_owl` (27%), `animals` (24%).
- Obie strony każdej z pięciu grup są zajęte przez co najmniej 1/5 profili (grupa 4: 48% `pos` i 30% `neg` po stronie nadawcy), więc losowa para ma 14–28% szansy na konflikt w największych grupach.
- Suma pięciu w przybliżeniu niezależnych zdarzeń: 1 − Π(1 − p_g) ≈ 53,8% przy p_g z tabeli; obserwowane 52,3% (niewielka zależność między grupami).
- Obserwowany odsetek jest w każdej grupie w granicach ±0,3 pp od poziomu oczekiwanego przy niezależności (grupa 0: o 0,3 pp niżej, grupa 3: o 0,1 pp wyżej). Konflikt nie jest więc ani częstszy, ani rzadszy niż przypadek: **zmienna ma wysoką prewalencję, a jej związek z doborem par w feedzie jest zerowy**.

## Skutek dla H1

Brak zmiany kodu zmiennej, więc brak zmiany ΔLL. Konsekwencja interpretacyjna: `lifestyle_tag_conflict` jest binarną zmienną o prewalencji ~52%, nieróżniącą się od losowej, więc jako miara „konfliktu stylu życia" ma niską zawartość informacyjną; wpływ na ΔLL bloku stylu życia zmierzono w przeliczeniu H1 na v1 (Z3/Z4). Dwie obserwacje opisowe, bez zmiany definicji:
(a) grupa 0 (palenie) pokrywa się treściowo z polem `smoking` (D13: tagi `smoker`/`non_smoker` uzupełniają pole), więc blok stylu życia może liczyć tę samą cechę dwa razy (zgodność pola i konflikt tagów);
(b) przejście v0 → v1 dodaje konflikt w 86 swipe'ach próby H1 (0,09%) i nie usuwa żadnego (przepięcie `peace_and_quite` do `likes_calm` przenosi go do grupy 4: 27,58% → 27,68%).
Zmiana definicji (np. usunięcie grupy 0 jako redundantnej z polem, próg częstości, wymóg obustronnej deklaracji) wykraczałaby poza oczywisty błąd i wymaga decyzji zespołu: **zapisane jako Q14 w `docs/h1/open-questions.md`**.

## Test

`tests/test_h1_d15.py`: znana liczba par z tagami po przeciwnych stronach daje dokładnie tyle konfliktów (także gdy para konfliktuje w dwóch grupach naraz); brak tagów nie daje konfliktu; `None`/`NaN` zamiast listy tagów nie daje konfliktu (wcześniej funkcja rzucała `TypeError`, teraz traktuje brak danych jako pusty zbiór; w danych nie występuje, więc zbiór się nie zmienia); wektorowa wersja zgadza się z funkcją produkcyjną na 300 losowych parach; baseline niezależności zgadza się z obserwacją, gdy strony są niezależne, i wykrywa zależność, gdy pary są doskonale przeciwne.
