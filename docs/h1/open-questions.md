# H1: otwarte kwestie po audycie (2026-11-08)

Źródło: `docs/h1/audit-fixes-2026-11-08.md`. Dla każdej niejednoznacznej decyzji wybrano opcję
bardziej konserwatywną i zapisano ją tutaj; do akceptacji przez zespół.

## 0. Odtworzenie liczb sprzed zmian

Odtworzone (bez rozbieżności). Specyfikacja `spec_old` na danych lokalnych daje: n = 92 754,
ΔLL styl życia = 41,379, ΔLL wiek+zainteresowania = 739,144, CV AUC (seed 42, foldy po nadawcach):
null 0,500, styl życia 0,519, wiek+zainteresowania 0,581, pełny 0,584. Notebook ma na to
asercję (sekcja 6.1). Nie zatrzymano pracy.

## 1. Decyzje niejednoznaczne i wybrana opcja

| # | Kwestia | Wybór (konserwatywny) | Alternatywa, której nie wykonano |
|---|---|---|---|
| O1 | Z1/Z2 mówią „płeć jest kontrolą”, Z4 mówi „demografia (wiek, `sex_pair`, miasto) jest blokiem”. | Kontrole (`sex_pair`, miasto) są w **każdym** modelu; blok „wiek” to trzy zmienne wieku. Dzięki temu blok stylu życia ma te same kontrole co pozostałe. Porównanie z karty (styl życia vs wiek+zainteresowania) zachowane. | Blok „demografia” z płcią i miastem w środku bloku. Zawyżyłby przyrost „demografii” kosztem stylu życia, jeśli płeć trafi tylko do jednego bloku. |
| O2 | Karta 3.2 wymienia `|Δ|`, `Δ`, `|Δ|²`; zadanie każe główną specyfikację bez kwadratu. | Główna: `same_band`, `age_band_diff_abs`, `age_band_diff`. Kwadrat i efekty stałe pasma nadawcy jako scenariusze wrażliwości. | Kwadrat w głównym modelu. |
| O3 | Karta 3.3 / A2 oraz D18 przewidują efekty losowe nadawcy i odbiorcy; estymator oznaczono `[DO POTWIERDZENIA]`. | Regresja logistyczna ze SE klastrowanymi dwustronnie (D18, kandydat 2) oraz CI różnic z **bootstrapu klastrowego**. GLMM (jak w H3a) nie został uruchomiony dla H1. | Model z crossed random effects (gpboost) i porównanie bloków przez LL modelu mieszanego. |
| O4 | 963 swipe'y bez żadnego wspólnie znanego pola stylu życia nie mają `lifestyle_agree_ratio`. | Odpadają z modelu głównego (n = 92 754; H2/H3a mają 93 717). W tabelach opisowych są kategorią „brak danych”. | Zostawić je z `ratio = 0` i wskaźnikiem braku. To zmieniłoby definicję miary, więc nie robiono tego po obejrzeniu wyników. |
| O5 | Kierunek palenia (Z7) bez codebooka (D14): kody `N`, `V`, `O`, `Y`. | `N` = niepalący, pozostałe kody = „użytkownik”. `V`/`O` interpretowane tylko jako „nie-`N`”. | Rozdzielenie `V` (vape?) i `O` po potwierdzeniu znaczenia kodów u dostawcy. |
| O6 | Rzadkie poziomy statusu pola (np. `both_missing` dla `cleanliness`: 3 swipe'y). | Poziomy < 50 swipe'ów łączone z „jedna strona brak”. | Brak łączenia (niestabilne OR, quasi-separacja). |
| O7 | Bootstrap „po odbiorcach” vs „po nadawcach”. | Raportowane oba; za konserwatywny przyjęto szerszy przedział. Bootstrap dwuwymiarowy (nadawca × odbiorca) nie został zaimplementowany. | Bootstrap dwustronny / pigeonhole. |
| O8 | CV po nadawcach: jeden podział na 5 foldów (seed 42), CI różnic z bootstrapu **na predykcjach out-of-fold**. | Bootstrap jest warunkowy na dopasowanych modelach foldów (bez ponownego uczenia), więc nie obejmuje zmienności uczenia. | Powtarzane CV z różnymi seedami i bootstrap z ponownym uczeniem. |
| O9 | Baseline permutacyjny zainteresowań (Z6b) permutuje zbiory hobby między swipe'ami w obrębie równej liczby tagów. | Permutacja na poziomie swipe'a nie zachowuje klastrowania po użytkownikach, więc jej p jest zbyt optymistyczne; do wniosku używamy CI z bootstrapu po nadawcach. Przy 500 permutacjach minimalne p = 1/501. | Permutacja na poziomie odbiorcy (całe profile). |
| O10 | Wagi IDF (Z6a). | df liczone na bieżących, oczyszczonych tagach hobby użytkowników bez Hyderabadu; tag nieznany dostaje wagę maksymalną log(N). | df liczone na ekspozycjach (swipe'ach). |
| O11 | ΔLL liczone na poziomie swipe'a zakłada niezależność obserwacji. | Traktujemy ΔLL jako miarę względną; o kryterium rozstrzygają CI różnic z bootstrapu klastrowego oraz testy Walda ze SE klastrowanymi (Z7). Różnica jest duża: np. `work_from_home` ma naiwne ΔLL = 54, a łączny test Walda p = 0,26. | Raportowanie wyłącznie ΔLL z p z testu LR (zawyżone). |
| O12 | A6 wymienia wrażliwość „z Hyderabadem” (D10). | Nie uruchomiono: wymaga przebudowy zbioru z Hyderabadem w próbie (poza zakresem zadania). | Dodać parametr `exclude_hyderabad` do `build_h1_dataset`. |
| O13 | Wiersze z `source_flag = first_version`/`users_current` w próbie głównej (D7). | Zostają w głównej (zgodnie z D7); wrażliwość „tylko `prior_version`” i „oba `prior_version`” raportowane. | Główna tylko na `prior_version` (n ≈ 46 863 przy obu stronach). |

## 2. Wady w artefaktach zespołu (zauważone, nie naprawiane)

- `docs/tag_category_proposal.csv` zawiera `bussiness` (literówka) zamiast `business`, które występuje w `docs/interests_mapping.csv`,
  oraz `often_outside`, którego nie ma w mapowaniu. Skutek: kanoniczny `business` nie ma kategorii w słowniku, więc
  `transform_and_disentangle_tags` zalicza go domyślnie do „unclear”, czyli do zainteresowań. Wpływ na wyniki prawdopodobnie mały, ale nie sprawdzono.
  To artefakt przeglądany przez ludzi (D11), więc go nie edytowano. Do decyzji: poprawić literówkę i przeliczyć.
- Liczba kanonicznych tagów: mapowanie ma 67 unikalnych, propozycja 68 wierszy, codebook (D.1) mówi 69.
- `uv.lock` na gałęzi nie zawiera grupy `embed` z `pyproject.toml`, więc każde `uv run` próbuje przeliczyć lock (zmiany nie zostały zacommitowane; używano `uv run --frozen`).
- `tests/test_eda.py` (3 testy) failuje bez `data/tables_metadata.json` (plik lokalny, poza gitem); niezwiązane z H1.
- Poprzedni lejek w notebooku (93 330) był błędny: krok „kompletne obserwacje” sprawdzał `same_band`, które nigdy nie jest NaN (brak pasma daje 0). Kolumny `same_band` nie zmieniono (kompatybilność); wiersze bez pasma wypadają przez `age_band_diff`. Do rozważenia: ustawiać `same_band = NaN` przy braku pasma.

## 3. Walidacja instrumentu AI (Z9): normalizacja i klasyfikacja tagów

**Stan w repo (sprawdzone w `docs/`, `notebooks/`, `src/`, `reports/`, `logs/ai/` i na wszystkich gałęziach):**
nie ma raportu zgodności normalizacji tagów (agent AI vs człowiek) ani żadnej wartości κ Cohena dla tagów.
`docs/codebook.md`, część D, **opisuje plan** walidacji, bez wyników. `scripts/gold_agreement.py` (gałąź `feat/gold-set`) dotyczy etykiet bio (H3), nie tagów.
Jedyna dostępna liczba: propozycje kategorii Claude i Gemini w `docs/tag_category_proposal.csv` są zgodne dla 58 z 68 tagów (85,3%); to zgodność dwóch agentów, **nie** walidacja względem człowieka i nie κ.
W raportach nie wolno podawać wartości κ, dopóki poniższe nie zostanie wykonane.

**Do zrobienia (zgodnie z D11, D19 i `docs/codebook.md` część D):**

1. **Zamrozić propozycje agenta przed adnotacją** (D19): zapisać commit z `tag_category_proposal.csv` i mapowaniem raw → kanoniczny, przed zamrożeniem codebooka.
2. **Próba:** (a) kategorie: wszystkie kanoniczne tagi (68/69, bez losowania; po poprawie literówki `business`), (b) mapowanie raw → kanoniczny: wszystkie 124 surowe ciągi (w tym 54 formy emoji), bo błąd mapowania wpływa na Jaccarda i na zgodność pól (D13), a codebook waliduje dziś tylko kategorie.
3. **Kto etykietuje:** trzy osoby (Dominik Czech, Michał Jankowski, Jakub Smolarczyk), niezależnie, **ślepo** względem propozycji agenta i siebie nawzajem; rozbieżności rozstrzygane wspólnie, wynik rozstrzygnięty = wzorzec.
4. **Metryki:** κ Cohena dla każdej pary adnotatorów i κ Fleissa dla trójki (sufit dla agenta), κ agent vs wzorzec z 90% CI, odsetek zgodności, macierz pomyłek; analiza błędów (formy emoji, `unclear`, granica lifestyle/hobby); przy małej próbie CI będzie szerokie i tak ma być raportowane.
5. **Zakres dodatkowy:** `TAG_TO_STRUCTURED_FIELD_MAP` (D13), grupy polaryzacji w `POLARITY_PAIRS` (D15) i uznanie `student` za status (D12) to też decyzje instrumentu; warto je dołączyć do tej samej sesji adnotacji.
6. **Miejsce raportu:** `reports/` lub `docs/h1/` z wartościami κ i linkiem w sekcji 10 notebooka `h1-hypothesis.ipynb`; wpis w `docs/ai-disclosure.md`.

## 4. Zależne od odpowiedzi dostawcy (karta 2.2, pyt. 2 i 4)

- Czy pola stylu życia są widoczne na karcie bez przewijania, czy tagi i bio są widoczne przed decyzją? Dopóki nie wiadomo, **brak efektu stylu życia nie oznacza braku wpływu** (cecha mogła nie być widoczna).
- Czy `cleanliness` i `noise_level` mają wartość domyślną (P6)? Jeśli tak, ich zgodność jest sztucznie zawyżona, a pomiar mniej informacyjny.
- Znaczenie kodów `V`, `O`, `Y` w `smoking` (D14, O5).
- Zdjęć profilowych nie ma w danych (G5); jakakolwiek teza o ich wpływie jest niezweryfikowaną hipotezą.

## 5. Rebase na v1 (2026-11-09): status pytań z walidacji tagów i nowe decyzje

Źródło: `docs/h1/rebase-v1-2026-11-09.md`. Pytania Q8–Q12 mieszkają w `docs/tag-validation/open-questions.md`
(plik decyzji człowieka, **nieedytowany**); ich status po rebase jest zapisany tutaj. Nowe pytania mają kolejne numery (Q13–Q18).

### 5.1 Status Q8–Q12

| # | Status | Ustalenie |
|---|---|---|
| Q8 | **otwarte** | Kody pola `lifestyle` (S/M/W) nadal bez znaczenia w codebooku; v1 używa mapy D13 z kodu (efekt uzupełniania pola przez `going_out_friends → often_out` = 0). Scenariusze diagnostyczne z kodem zastępczym `OUT` są założeniem, nie danymi, i nie są podstawą wniosków. |
| Q9 | zamknięte | `peace_and_quite → likes_calm` jest w v1. Skutek na konflikt D15: v0 → v1 dodaje konflikt w 86 swipe'ach próby H1 (0,09%), żadnego nie usuwa; jeden tag nie zmienia ΔLL bloku stylu życia istotnie (dekompozycja: −0,08). |
| Q10 | **zamknięte** | Konflikt D15 52% to **prawdziwa prewalencja**, równa poziomowi przy niezależności stron (52,3% vs 52,4%). Brak błędu implementacji, brak zmiany kodu. Szczegóły: `docs/h1/d15-conflict-investigation.md`. |
| Q11 | bez zmian | 8 nadpisań A weszło do v1 (3 z nich to tylko zmiana etykiety `business` → `bussiness`, ΔLL 0,000). |
| Q12 | **zamknięte** | Przedziały ufności dla różnic między słownikami policzone (bootstrap po nadawcach i odbiorcach, B = 1000, parami: te same losowania): `reports/h1/rebase/dictionary_change_vs_v0.csv`. |

### 5.2 Nowe decyzje niejednoznaczne (wybór konserwatywny)

| # | Kwestia | Wybór | Alternatywa, której nie wykonano |
|---|---|---|---|
| Q13 | **Definicja D15.** W kodzie są **pięć** grup polaryzacji (nie cztery jak w opisie zadania), konflikt ma prewalencję ~52% i nie różni się od przypadku. Grupa 0 (palenie) dubluje pole `smoking`, które D13 uzupełnia tymi samymi tagami. | Definicja bez zmian; zmiana wykracza poza oczywisty błąd (zasada 7). **Decyzja zespołu.** | Wyrzucić grupę 0 jako redundantną z polem; wymagać obustronnej deklaracji; zastąpić zmienną liczbą grup w konflikcie. Każda zmieni ΔLL bloku stylu życia i wymaga ponownego zamrożenia kontraktu. |
| Q14 | **Rozbieżność `bussiness`.** `decisions.md` (pkt „Niezgodności z Claude") podaje `bussiness`: `unclear` → `hobby`, a `consensus_B.csv` ma dla `bussiness` konsensus `unclear` (zgodny z agentem). Kod używa pliku CSV. Poprawna pisownia `business` nie ma wpisu w propozycji (kategoria domyślna `unclear`). | v1 używa CSV (`unclear`). W kodzie `unclear` trafia do zainteresowań jak `hobby`, więc skutek na dane i ΔLL wynosi 0. Plik `decisions.md` nie był edytowany; do uzgodnienia przez człowieka. | Przepisać CSV na `hobby` (bez skutku na wynik). |
| Q15 | **Przedziały ufności samych przyrostów ΔLL.** Percentylowy bootstrap klastrowy przyrostów ΔLL (nie różnic) jest asymetryczny i przesunięty w górę względem estymaty punktowej (np. zainteresowania w v0: 13,9 [2,3; 101,4]). Stosunek styl życia / zainteresowania ma przez to bardzo szeroki przedział (v0: 3,05 [0,27; 26,0]). | Raportowane jak w audycie (percentyle, bez korekty obciążenia); kryterium H1 opiera się na przedziałach **różnic** przyrostów, jak dotąd. | Bootstrap BCa lub studentyzowany; przedział z asymptotyki Walda dla ΔLL. |
| Q16 | Tolerancja 1e-3 przy odtworzeniu v0. Audyt podaje ΔLL do 2 miejsc (533,19 / 13,93 / 42,51), więc zgodność do 1e-3 z wartością surową jest niemożliwa. | Porównanie po zaokrągleniu do 2 miejsc (zgodne); surowe odchylenia ≤ 0,0036 to sam błąd zaokrąglenia. Dla CI różnic odtworzono wartości z audytu z dokładnością do 0,1 (−504,5 [−883,4; −300,8]). | Porównanie z pełną precyzją z logu audytu (niedostępną). |
| Q17 | Liczba powtórzeń bootstrapu CV: audyt 500, tutaj **1000** (wymóg B ≥ 1000). | v0 i v1 liczone z tym samym B = 1000; CI v0 różnią się od audytu co najwyżej w 4. miejscu po przecinku (np. AUC jako blok pierwszy, styl życia − zainteresowania: +0,0075 [0,0013; 0,0139] w audycie, +0,0075 [0,0017; 0,0137] tutaj). | B = 500 jak w audycie. |
| Q18 | Nagłówek „demografia wygrywa, deklarowane dopasowanie dodaje niewiele" z zadania nie występuje w dotychczasowych tekstach H1 w repo. | Użyty jako nagłówek podsumowania; „demografia" = wiek (blok wieku) wraz z kontrolami płci i miasta, „deklarowane dopasowanie" = styl życia i zainteresowania. Zweryfikowane liczbami (udział wieku w ΔLL 91%). | Inne sformułowanie, jeśli zespół ma wersję z plakatu lub slajdów. |
