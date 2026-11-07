# Prompt dla agenta Claude Code: H3a, poziom 3 (diagnostyka, SE dla GLMM, figury)

Zapisz jako `docs/prompts/h3a-level3-prompt.md` i podaj agentowi ścieżkę. Dominik Czech, 2026-11-03.
Ten prompt **uzupełnia** `docs/prompts/h3a-notebook-prompt.md` (dalej „prompt 1”). Wszystkie twarde
zasady z jego sekcji 2 (prywatność, tylko agregaty, brak zewnętrznych API, seed, brak edycji
`codebook.md`, logi AI, wpis do `docs/ai-disclosure.md`) i sekcji 13 obowiązują bez zmian.
Gałąź: ta, na której pracujesz (`banacchini/h3-notebook`), małe commity, bez `push`.

**Zakres: wyłącznie H3a.** Składanie slajdów (Typst) jest robione w osobnym prompcie i nie należy do
tego zadania. Poziom 3 dostarcza tylko **liczby i figury** w formie, którą tamten prompt może wprost
wczytać (sekcja 4).

---

## 0. Kontekst i cel

Poziomy 1 i 2 zakończyły się w ok. 20 min z budżetu 3 h. Wyniki: `reports/h3a/summary_level2.md`,
`docs/h3a/decision-log.md`. Stan, który poziom 3 ma poprawić lub wyjaśnić:

- M1 (GLMM) zbiega, ale GPBoost nie liczy SE (numeryczny Hessian nie jest dodatnio określony), więc
  etykieta „potwierdzony” opiera się na M2 (fallback), a reguła zgodności M1 = M2 nie została sprawdzona.
- S2a (tylko swipe'y z `prior_version`): M2 daje OR 1,064 (CI 0,972–1,165, „nierozstrzygający”),
  M3 zostaje przy 1,174. Prawdopodobna heterogeniczność wg pochodzenia cech as-of / „wieku” konta.
- Płeć nadawcy: kobiety OR 1,26, mężczyźni 1,03, interakcja p = 0,020 (S8, zaplanowana).
- Wykresy mają być **intuicyjne i atrakcyjne wizualnie**, zrozumiałe dla osoby spoza zespołu. Posłużą
  zarówno do preprintu i plakatu, jak i (przez osobny prompt) do slajdów.

Bloki: **A** diagnostyka, **B** błędy standardowe dla GLMM, **C** liczby i figury, **D** porządki.

## 1. Dyscyplina wnioskowania (ważne)

- **Reguła werdyktu, margines 0,10 i lista S1-S8 pozostają bez zmian.** Etykieta z poziomu 2 nie jest
  nadpisywana po cichu. Poziom 3 może ją co najwyżej **uzupełnić adnotacją** (np. „wrażliwy na
  specyfikację”) albo, jeśli blok B da SE dla M1, **sprawdzić regułę zgodności M1 = M2**, która była
  w planie od początku.
- Wszystko w bloku A oznacz w decision-logu i w `summary_level3.md` jako **„diagnostyka post hoc,
  zainicjowana wynikiem S2a”** (poza interakcją po płci, która była zaplanowana jako S8). Bez
  twierdzeń potwierdzających, bez poprawek na wielokrotność, ale z jawnym zastrzeżeniem.
- **Nie stratyfikuj po odsetku prawych swipe'ów nadawcy ani po żadnej zmiennej liczonej z `y_right`**
  (warunkowanie na wyniku obciąża estymator). Selektywność nadawcy jest już kontrolowana przez M3 (FE).

## 2. Blok A: diagnostyka

Każda analiza: M2 (pooled logit, klastrowanie dwukierunkowe) **i** M3 (FE nadawcy, klastrowanie po
odbiorcy), próba główna jak w poziomie 2, te same kontrole. Wyniki do `reports/h3a/tables/` i do cache.

- **A1. Wszystkie próby GPBoost.** Przefituj każdą z 4 konfiguracji optymalizatora z D-H3a-9 i zapisz
  dla każdej: `beta_has_bio`, wariancje efektów losowych, log-likelihood, kod zbieżności, czas.
  Cel: sprawdzić, czy β = 0,130 z niezbieżnej próby jest reprezentatywne, i które próby zbiegły
  (kod 0) z jakim β. Oczekiwane: β bliższe M3 niż M2 przy wariancji nadawcy ≈ 7,8. Jeśli tak nie
  jest, zapisz to jako anomalię w decision-logu.
- **A2. Heterogeniczność wg pochodzenia cech i „wieku” konta (diagnoza S2a).**
  - `asof_prior` = `asof_source == "prior_version"` (poziom pary, D-H3a-5). Model z interakcją
    `has_bio × asof_prior` (test Walda, klastrowane SE) oraz osobne estymacje na obu połówkach:
    `prior_version` (to jest S2a) i dopełnienie (`first_version` / `users_current`).
  - `sender_account_age_days = swipe_day − dzień pierwszej wersji nadawcy`, kosze **ustalone z góry:**
    `0`, `1-7`, `≥ 8`. Analogicznie `receiver_profile_age_days` (dzień swipe'a − dzień pierwszej wersji
    odbiorcy), te same kosze. Dla każdego koszyka OR (M2, M3) z CI i test interakcji osobno dla nadawcy i
    odbiorcy. Użytkownicy bez historii (9) wyłączeni z A2 i policzeni.
  - Cel: ustalić, czy efekt jest skoncentrowany w swipe'ach z dnia założenia konta (nadawcy) lub w
    nowych profilach (odbiorcy) i czy M2 jest wrażliwy na skład nadawców, a M3 nie. Zaraportuj
    wynik jednoznacznie, także gdy brak heterogeniczności.
- **A3. Stabilność współczynnika po dodawaniu kontroli.** Sekwencja specyfikacji (jedna próba, ten sam
  zestaw wierszy): `has_bio` → `+ demografia` (`sex_pair`, `age_band_diff`, `same_band`, `same_city`) →
  `+ profile_completeness` → `+ tag_count_receiver (z flagami)` (= specyfikacja główna). OR i CI dla
  `has_bio` w każdym kroku, M2 i M3. Wykres „schodkowy” (C4 w sekcji 4.5) i tabela.
- **A4. E-value** (VanderWeele-Ding) dla `has_bio`: M2 i M3 (punkt i granica CI bliższa 1), płeć nadawcy
  F i M. Użyj przybliżenia RR ≈ √OR (wynik częsty, baza ≈ 20%), formuła `E = RR + √(RR·(RR−1))`
  (dla OR < 1 odwróć). Podaj założenia i zastrzeżenie, że to miara czułości, nie dowód braku
  konfundowania.
- **A5. Prawdopodobieństwa standaryzowane i średni efekt krańcowy.** Z M2 estymowanego **osobno dla F i
  M** (oraz dla całej próby): średnie przewidywane P(prawy swipe) przy `has_bio = 0` i `= 1` dla
  wszystkich swipe'ów w warstwie; różnica w p.p. z 95% CI (delta method, macierz klastrowana jak w
  D-H3a-12). Zapisz także wersję „na 100 swipe'ów” (zaokrąglenie do 0,1). Jeśli warstwa O ma za mało
  danych (jak w S8), pomiń ją i zaznacz. Policz też AME w p.p. (M2) dla **każdej** specyfikacji S1-S8,
  bo korzysta z tego figura C-wersji (sekcja 4.2).

## 3. Blok B: SE dla GLMM (M1)

Cel: dostać wiarygodne wnioskowanie dla `has_bio` z modelu ze skrzyżowanymi efektami losowymi
albo jednoznacznie stwierdzić, że się nie da. Drabina; kolejne szczeble tylko jeśli poprzedni nie daje CI.

- **B1. Test ilorazu wiarygodności (GPBoost).** Dopasuj M1 z `has_bio` i M1 **bez** `has_bio` (ta sama
  konfiguracja optymalizatora, obie próby muszą mieć kod zbieżności 0; przetestuj konfiguracje z
  D-H3a-9, wybierz pierwszą, która zbiega w obu). Statystyka `2·(ℓ_pełny − ℓ_zerowy)` ~ χ²₁, p-value.
  Sprawdź w dokumentacji GPBoost, czy `fit` obsługuje offset w części stałej; jeśli tak, zrób
  profil wiarygodności dla β_bio (siatka co najmniej 9 punktów wokół oszacowania) i odczytaj CI 95% i
  90% z progu χ². Jeśli offset nie jest obsługiwany, raportuj tylko p-value LRT. **Bez CI nie
  stosujesz `classify`**; zapisz, że daje to test istotności, nie test równoważności.
- **B2. `lme4` w R.**  R i `lme4` są już zainstalowane.
  - Sprawdź `Rscript` i `Rscript -e 'library(lme4)'`.
  - Zmodyfikuj `analysis.lme4_crosscheck`, by wymiana danych szła przez **CSV w katalogu tymczasowym**
    (`mktemp -d`, uprawnienia 0700, kody całkowite zamiast identyfikatorów, usunięcie po zakończeniu),
    bez `arrow`. Dodaj test jednostkowy na małej próbie z symulacji (odtworzenie znanego β).
  - Model: `glmer(..., family = binomial, nAGQ = 0, control = glmerControl(optimizer = "bobyqa",
    optCtrl = list(maxfun = 2e5)))` ze skrzyżowanymi `(1|sender) + (1|receiver)`, ta sama specyfikacja
    co M1, timeout `FIT_TIMEOUT_MIN`. Raportuj OR z CI Walda (95% i 90%), wariancje, ostrzeżenia
    o osobliwości i zbieżności, czas. Jeśli czas pozwala, dodaj LRT (`anova` względem modelu bez `has_bio`).
  - Uruchamiane także osobno: `scripts/run_h3a.sh 3 only=lme4`, żeby Dominik mógł to odpalić po
    doinstalowaniu R samodzielnie.
- **B3. Ostateczność (tylko gdy `RUN_BOOTSTRAP=1`, domyślnie wyłączone, przeznaczone na noc):**
  bootstrap po nadawcach (B = 200, z cache co 10 powtórzeń, timeout na całość 3 h) dla β_bio z
  GPBoost; SE i percentylowe CI. Zaznacz w raporcie, że resampling nadawców nie odtwarza w pełni
  struktury skrzyżowanej.
- **Raportowanie bloku B:** tabela `szczebel | co uzyskano | β | SE lub p | CI | status`.
  Jeśli CI dla M1 powstało (B2 lub B3), uruchom `classify` i **sprawdź regułę zgodności M1 = M2**;
  zapisz wynik w `summary_level3.md`. Jeśli powstało tylko p-value LRT, zapisz, czy potwierdza kierunek,
  ale reguła zgodności pozostaje niesprawdzona. Zestawienie GPBoost vs `lme4` (β, wariancje) to
  osobny wiersz kontroli estymatora; rozbieżność oznacz „wrażliwy na estymator”.

## 4. Blok C: liczby i figury (bez składu slajdów)

### 4.1 Zadanie

Wyprodukuj **trzy intuicyjne figury H3a** (A, B, C) w formie **samego wykresu**, gotowej do osadzenia
w Typst (preprint, plakat, slajd), oraz **jedno źródło liczb** dla osoby składającej slajdy. Nie składaj
slajdów, nie generuj `.pptx` ani `.typ`, nie dodawaj tytułów slajdów i stopek do figur (tytuł i wniosek
doda skład w Typst). Figury mają być czytelne w 5 sekund, bez żargonu (bez OR, CI, GLMM na figurach A i B),
**uczciwe** (pokazują niepewność, nie sugerują przyczynowości) i **atrakcyjne** (sekcja 4.3).

Wszystkie liczby na figurach pochodzą z A5 i zapisanych wyników. Nie wpisuj niczego ręcznie. Tłumienie
komórek < 5 i zasady z promptu 1 (§2, §10) obowiązują.

### 4.2 Trzy figury

- **Figura A (główna): „bez bio vs z bio”, dwa panele: kobiety jako nadawcy i mężczyźni jako nadawcy.**
  Dla każdego panelu dwa punkty (bez bio / z bio) połączone grubą strzałką, **bardzo duże etykiety
  procentów** (np. „14,5%” → „17,2%”) i adnotacja różnicy „+2,7 p.p.” z drobnym zakresem „95%: 1,4-4,0”
  (wartości z A5). Oś od 0 (bez przycinania, żeby nie powiększać różnicy), bez siatki, bez legendy
  (etykiety bezpośrednio przy punktach).
- **Figura B: „na 100 swipe'ów”.** Cztery siatki kropek 10 × 10 (kobiety: bez bio / z bio; mężczyźni:
  bez bio / z bio); wypełnione kropki to prawe swipe'y (zaokrąglone przewidywane liczby z A5), reszta
  jasnoszara. Pod siatką liczba i drobny zakres. Cel: intuicja bez statystyki.
- **Figura C: „czy wynik się trzyma?”.** Uproszczony wykres odporności: jeden wiersz na test, **efekt w
  p.p.** (AME z M2 dla każdej specyfikacji z A5), pionowa linia 0, pas „praktycznie zero” (±1,5 p.p.).
  Etykiety w języku potocznym („model podstawowy”, „tylko aktywni użytkownicy”, „z kontami z
  Hyderabadu”, „tylko swipe'y z pewną wersją profilu”). **Wyjątek S2a ma być widoczny i opisany
  uczciwie** (adnotacja „połowa próby; efekt słabszy”), nie ukryty. M3 jako drugi znacznik w wierszu.

### 4.3 Projekt wizualny (obowiązkowy)

- **Płótno:** 16:9, 13,33 × 7,5 cala (skład może skalować); eksport **SVG z tekstem jako tekstem**
  (`svg.fonttype = "none"`) i PNG 200 dpi. **Tło przezroczyste** (osobny wariant PNG z białym tłem jako
  podgląd). Pliki: `reports/h3a/export/h3a_fig_{A,B,C}.svg|png`.
- **Typografia:** liczby-bohaterowie 44-60 pt, etykiety ≥ 20 pt, drobny druk ≥ 14 pt. Jedna rodzina
  fontu (bezszeryfowa, dostępna lokalnie, z poprawnym polskim; nie pobieraj nic z sieci). Polski przecinek
  dziesiętny i niełamliwe spacje przy liczbach i jednostkach.
- **Kolor (Okabe-Ito, bezpieczny dla daltonistów):** „bez bio” = szary `#6B7280`, „z bio” = niebieski
  `#0072B2`, wyróżnienie/zastrzeżenie = pomarańcz `#D55E00`, tekst `#1F2937`. Maksymalnie 3 kolory
  akcentowe. Kontrast tekstu do jasnego tła ≥ 4,5:1 (sprawdź programowo).
- **Układ:** jedna idea na wykres, bezpośrednie etykiety zamiast legend, brak ramek i siatek, duże
  marginesy, kropki, strzałki i duże liczby zamiast tabel.
- **Motyw dla reszty zespołu:** wyeksportuj `reports/h3a/export/theme.json` (paleta, fonty, rozmiary,
  marginesy) i krótki `theme.py` z funkcją stylu, żeby autorzy H1 i H2 mogli użyć tego samego wyglądu.
  Nie edytuj ich kodu.
- **Pętla kontroli wizualnej:** po wygenerowaniu **obejrzyj PNG** (narzędzie do podglądu obrazów) i popraw:
  nachodzące etykiety, ucięty tekst, zbyt mały druk, niezrównoważony układ. Co najmniej 2 iteracje na
  figurę; programowo sprawdź minimalny rozmiar fontu i kontrast. W raporcie podaj, co poprawiłeś.

### 4.4 Źródło liczb i podpisy dla składu

- `reports/h3a/export/h3a_numbers.json`: **jedno źródło prawdy** dla osoby składającej slajdy. Zawiera
  wszystkie liczby użyte w figurach i w streszczeniu wyniku: A5 (P bez/z bio, różnica w p.p., CI, F, M i
  całość), OR z CI dla M1/M2/M3, AME, S1-S8, S8 z interakcją, M5, M6, lejek M4, N swipe'ów i nadawców,
  wynik A2/A3/A4, status M1 (SE lub brak). Każda liczba w dwóch formach: surowa i `*_pl` (sformatowana
  po polsku, przecinek dziesiętny, niełamliwe spacje). Dodaj `generated_at`, `seed`, hash danych.
- `reports/h3a/export/h3a_captions.md` (po polsku, zwięźle): dla każdej figury podpis (1-2 zdania),
  tekst alternatywny, **3 warianty tytułu-wniosku** (od najostrożniejszego do najbardziej odważnego, każdy
  zgodny z wynikami) oraz jedno zdanie ograniczeń („związek, nie przyczyna”; brak zdjęć; ekspozycja przez
  feed; M1 bez SE, jeśli nadal aktualne).

### 4.5 Poprawki i nowe figury do preprintu

- F1: dopisz N (swipe'y, nadawcy, odbiorcy) i etykiety wartości.
- F3: w legendzie opisz grubość słupków (gruba = 90%, cienka = 95% CI) i dodaj wiersz „GLMM (punkt, bez CI)”
  lub CI, jeśli blok B je da.
- F4: etykiety „Kobiety (M2)”, „Kobiety (M3)” itd. zamiast „F · M2”.
- F5: oś Y „OR względem mediany długości” zamiast „95 znaków”; zaznacz gęstość (rug) agregatem.
- Nowe: **C4** (stabilność współczynnika po dodawaniu kontroli, A3) i **C5** (heterogeniczność wg
  pochodzenia cech i „wieku” konta, A2), w stylu z sekcji 4.3, z zapisem PNG + SVG + CSV danych i wpisem
  do `figures_manifest.csv`.

## 5. Blok D: porządki

- **Decision-log:** nowe wpisy `D-H3a-28...` (każdy z datą, uzasadnieniem, źródłem). Przepisz sekcję
  **„Wybór estymatora do obrony ustnej”** tak, żeby opisywała stan faktyczny (M2 jako fallback; GLMM tylko
  punktowo, albo z CI/LRT, jeśli blok B je dał; M3 jako kontrola nadawcy; różne estymandy M2 vs M3 przy
  dużej wariancji nadawcy). Oznacz jako **„szkic do akceptacji Dominika”**; 2-3 zdania. Nie zmieniaj statusu
  wpisów [default agenta] z poziomów 1-2 (Dominik je zatwierdzi).
- **Logi sesji:** plik `logs/ai/claude/banacchini/2026-11-02-h3a-notebook.jsonl` przekracza limit hooka.
  **Nie obchodź hooka i nie zmieniaj jego limitu.** Przygotuj w katalogu poza gitem podział na części
  ≤ 900 KB po granicach linii (z sumą SHA-256 oryginału i scalenia), pokaż polecenia i **zatrzymaj
  się** do decyzji Dominika. To samo dotyczy logu bieżącej sesji.
- **Testy** (`pytest`): E-value, interakcja i warstwy w A2 (kosze wieku), schodkowe kontrole A3, A5 (zgodność
  z ręcznym przeliczeniem na małej próbie), LRT (statystyka z dwóch zadanych log-likelihoodów), format
  `*_pl` w `h3a_numbers.json`, `classify` dla przypadków dodanych. Nie naprawiaj 3 testów
  `tests/test_eda.py` (nie dotyczą H3a); zgłoś.
- **Dokumentacja:** `docs/h3a/README.md` (uruchamianie poziomu 3 i `only=`), `summary_level3.md`
  (generowany), wpis w `docs/ai-disclosure.md`.

## 6. Budżet, uruchamianie, raport

- Parametry notebooka: `RUN_LEVEL = 3`, `ONLY` (`diagnostics` | `se` | `figures` | `lme4` | pusty =
  wszystko), `RUN_BOOTSTRAP = 0`. Cache jak wcześniej (fity z poziomów 1-2 z cache). `scripts/run_h3a.sh 3`.
- Kolejność: **A5 → C (figury i liczby) → A1-A4 → B1 → B2 → D**, bo figury zależą tylko od A5, a
  Dominik chce je zobaczyć najwcześniej. B3 tylko na życzenie.
- Szacunek: A1-A5 kilka minut, B1 kilka-kilkanaście minut, B2 zależnie od R (do 90 min), reszta minuty.
- **`reports/h3a/summary_level3.md`** (generowany): (1) co zmienia się względem poziomu 2 (domyślnie: nic w
  etykiecie), (2) wyniki A1-A5 w tabelach z krótkim komentarzem i oznaczeniem „post hoc”, (3) wynik bloku B i
  ewentualna kontrola zgodności M1 = M2, (4) lista plików w `reports/h3a/export/`.
- **Raport końcowy do Dominika** (zwięźle): czy diagnoza S2a jest potwierdzona (A2) i jak zmienia przekaz;
  co dał blok B (w tym czy R się zainstalowało); którą z figur A/B/C polecasz do slajdu i dlaczego; co
  poprawiłeś w pętli wizualnej; pytania do decyzji (logi sesji, ewentualne polecenia instalacji R, jeśli
  `sudo` wymagało hasła).

## 7. Czego nie robić

- Nie składaj slajdów, nie generuj `.pptx` ani `.typ` (osobny prompt); nie instaluj `python-pptx`.
- Nie zmieniaj marginesu, reguł etykiet, S1-S8 ani definicji zmiennych; nie dodawaj H3b ani NLP.
- Nie stratyfikuj po zmiennych liczonych z `y_right`.
- Nie wpisuj liczb na figurach ręcznie ani nie zaokrąglaj w sposób sugerujący większy efekt.
- Nie ukrywaj S2a, braku SE w M1 ani niepewności; figury mają być atrakcyjne, ale wierne wynikom.
- Nie obchodź hooków repo, nie wyświetlaj danych wierszowych ani tekstu bio; Nie instaluj pakietów systemowych - R jest już zainstalowane.
