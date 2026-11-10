# H3a: dziennik decyzji

Decyzje podjęte przy budowie analizy H3a (`src/rentfriends/h3a/`, `notebooks/H3a.ipynb`).
Źródło: `docs/prompts/h3a-notebook-prompt.md` (dalej „prompt”), decyzje D1-D22
(`docs/prompts/m1-generation-plan.md`) albo **[default agenta]** (agent Claude Code wybrał
opcję domyślną lub najbardziej zachowawczą; do akceptacji przez Dominika).
Wszystkie wpisy z 2026-11-02.

## D-H3a-1 Zakres przebiegu: pełne badanie bez zatrzymania po pilocie
- Decyzja: po udanym smoke teście (`SAMPLE_FRAC = 0.1`) uruchomiono od razu poziom 1 i poziom 2 na
  pełnych danych, z budżetem maks. 3 h.
- Uzasadnienie: polecenie Dominika w sesji („po przejściu pilota uruchom pełne badania tak, żeby
  trwały max 3 godziny; nie czekaj na akceptację”) zmienia punkt zatrzymania z §12 promptu.
- Źródło: Dominik (polecenie w sesji).

## D-H3a-2 Gałąź `banacchini/h3-notebook` zamiast `h3a-notebook` [default agenta]
- Decyzja: praca na istniejącej gałęzi `banacchini/h3-notebook` (utworzonej przez Dominika,
  równej `main`), a nie na nowej `h3a-notebook`.
- Uzasadnienie: sprzeczność promptu ze stanem repo; gałąź była już przygotowana do tej pracy.
- Odrzucone: tworzenie drugiej gałęzi.

## D-H3a-3 Reguła as-of z D7 i §4 promptu
- Decyzja: wersja profilu = ostatnia wersja z dniem < dzień swipe'a (`prior_version`); swipe w dniu
  pierwszej wersji lub wcześniej → wersja o najniższym numerze (`first_version`); użytkownicy bez
  historii → bieżące `users` (`users_current`).
- Uzasadnienie: codebook (część C) odwołuje się do „as-of rule from section 0”, której w pliku nie
  ma (zgłoszone jako luka).
- Źródło: prompt, D7.

## D-H3a-4 Kilka wersji jednego dnia [default agenta]
- Decyzja: z wersji z tego samego dnia przed dniem swipe'a bierzemy tę o najwyższym numerze
  (stan na koniec dnia); `first_version` = najniższy numer wersji.
- Uzasadnienie: w `profile_history` jest 1911 par (użytkownik, dzień) z więcej niż jedną wersją.
- Odrzucone: pierwsza wersja dnia (stan, którego nikt nie widział na końcu dnia).

## D-H3a-5 `asof_source` na poziomie pary [default agenta]
- Decyzja: para = `prior_version`, gdy obie strony mają `prior_version`; `users_current`, gdy
  którakolwiek strona ma `users_current`; w pozostałych przypadkach `first_version`. S2a używa
  swipe'ów z `prior_version` po obu stronach.
- Uzasadnienie: prompt definiuje `asof_source` bez rozróżnienia stron; wariant obustronny jest
  najbardziej zachowawczy. Udziały po stronach zapisane w `reports/h3a/results.json`.

## D-H3a-6 Cztery polskie etykiety tagów spoza mapowania [default agenta]
- Decyzja: `💻 Pracuję zdalnie` → `works_remote`, `🏃 Aktywność & sport` → `active_sport`,
  `🤫 Spokojne wieczory` → `quiet_evenings`, `🧵 DIY / rękodzieło` → `diy` (w kodzie,
  `config.EXTRA_TAG_MAP`; `interests_mapping.csv` nie zmieniony).
- Uzasadnienie: w danych jest 128 surowych ciągów, w mapowaniu 124; te cztery to polskie wersje
  etykiet emoji z angielskimi odpowiednikami w mapowaniu. Łącznie 6 wystąpień, wpływ na H3a
  pomijalny. Pozostałe niezmapowane ciągi zachowałyby własny slug (codebook B.1).
- Odrzucone: edycja mapowania (mapowanie czeka na review człowieka).

## D-H3a-7 Konta Hyderabad
- Decyzja: wykluczamy konta z bieżącym `users.city = 'Hyderabad'` (45; tyle samo kont ma
  Hyderabad w jakiejkolwiek wersji historii) jako nadawcę lub odbiorcę: 849 swipe'ów na profile
  (669 jako nadawca, 627 jako odbiorca, część w obu rolach). Zgodne z D10.
- Źródło: prompt, D10.

## D-H3a-8 G18: rozbieżność `bio_length` [default agenta]
- Decyzja: `bio_len` liczone z tekstu po `strip()`; rozbieżność z `bio_length` liczona względem
  długości surowego tekstu (bez strip). Wynik: 2,0% snapshotów odbiorców widzianych w swipe'ach,
  2,6% swipe'ów.

## D-H3a-9 GPBoost 1.8: SE, intercept, optymalizatory [default agenta]
- Decyzja: (a) `params={"std_dev": True}` z promptu jest w GPBoost 1.8 wycofane (błąd), SE z
  `get_coef(std_err=True)` i `get_cov_pars(std_err=True)`; (b) kolumna interceptu `const` dodana
  jawnie (bez niej GPBoost ostrzega i nie estymuje wyrazu wolnego); (c) przy braku zbieżności lub
  NaN w SE (numeryczny Hessian nie PD, zdarza się przy domyślnej tolerancji) kolejne próby:
  `lbfgs` → `gradient_descent` → `gradient_descent` z `delta_rel_conv = 1e-8` → `lbfgs` z
  `delta_rel_conv = 1e-8`. Akceptowany pierwszy fit ze statusem zbieżności 0 i skończonymi SE.
  Wszystkie próby zapisane w wynikach.
- Uzasadnienie: prompt każe sprawdzić dokumentację i przy braku zbieżności zmienić optymalizator.
- Odrzucone: `nelder_mead` (w testach także NaN w SE), `fisher_scoring` (niedostępny dla
  bernoulli_logit).

## D-H3a-10 Standaryzacja i kategorie referencyjne [default agenta]
- Decyzja: standaryzowane (z-score w obrębie dopasowywanej próby): `age_band_diff`,
  `profile_completeness(_alt)`, `tag_count_receiver` / `tag_count_raw`. Zmienne binarne bez zmian.
  Referencje: `sex_pair = F→F`, `same_city = same`, `receiver_age_band = 18-20`, pola stylu
  życia: „brak”.
- Uzasadnienie: współczynnik `has_bio` nie zależy od standaryzacji kontroli.

## D-H3a-11 Separacja i współliniowość w designie [default agenta]
- Decyzja: wskaźniki binarne z pełną separacją (wynik stały tam, gdzie wskaźnik = 1) oraz kolumny
  będące dokładną kombinacją liniową wcześniejszych są usuwane z designu dla wszystkich modeli
  danej specyfikacji; `has_bio` nigdy. Lista usuniętych kolumn zapisywana przy każdym ficie
  (`dropped_separated`, `dropped_collinear`). Przykłady: `sex_pair=O→O` w próbie 10%,
  `ls_smoking=Y` (separacja) i `ls_noise_level=R` (współliniowe) w S7.
- Uzasadnienie: MLE dla takich kolumn nie istnieje, a Hessian logitu jest osobliwy.

## D-H3a-12 M2: własna implementacja CGM i AME [default agenta]
- Decyzja: klastrowanie dwukierunkowe Camerona-Gelbacha-Millera V = V_nadawca + V_odbiorca −
  V_przecięcie (CRV1, korekta G/(G−1)·(N−1)/(N−K)); przy macierzy nie-PSD obcięcie ujemnych
  wartości własnych (flaga). AME = średni dyskretny efekt `has_bio` (p. p.), SE metodą delta z
  macierzą klastrowaną.
- Weryfikacja: na pełnych danych SE identyczne z `statsmodels` (`cov_type="cluster"` z dwiema
  kolumnami grup, `cov_cluster_2groups`) i AME identyczny z `get_margeff(dummy=True)` (różnica
  względna ~1e-15).

## D-H3a-13 M3: logit z FE nadawcy, profilowany Newton [default agenta]
- Decyzja: efekty stałe nadawcy profilowane dokładnie (krok β z dopełnienia Schura, wyniki
  wycentrowane w obrębie nadawcy z wagami p(1−p)); to jest MLE z dummies (test jednostkowy:
  zgodność współczynników i SE z `statsmodels` Logit z dummies do 1e-6). SE klastrowane po
  odbiorcy, K w korekcie obejmuje liczbę FE. Nadawcy z samymi 0 lub 1 odpadają. `sex_pair`
  kodowane jako płeć odbiorcy w obrębie płci nadawcy (referencja X→F dla każdej płci nadawcy),
  bo efekt główny płci nadawcy jest wchłaniany przez FE; bez tego współczynniki O→F, O→M
  rozbiegały się. Kolumny liniowo zależne od FE usuwane (`has_bio` sprawdzane pierwsze).
- Odrzucone: `ConditionalLogit` (koszt kombinatoryczny dla nadawców z tysiącami swipe'ów) i
  gęste dummies (ok. 1500 kolumn × 93 tys. wierszy).

## D-H3a-14 M5: dwie specyfikacje długości [default agenta]
- Decyzja: (a) liniowo `log1p(bio_len)` + `bio_len_cap` (M1 i M2) → OR na podwojenie =
  exp(β·ln 2); (b) naturalny spline sześcienny (patsy `cr`, 3 df, centrowany) na `log1p(bio_len)`
  + `bio_len_cap` → krzywa dose-response z M2 (referencja: mediana długości niepustych bio).
- Uzasadnienie: zapis promptu „log1p + spline + cap” rozdzielony na efekt na podwojenie i krzywą;
  krzywa z M2, bo GPBoost nie udostępnia pełnej macierzy kowariancji współczynników.

## D-H3a-15 M6 [default agenta]
- Decyzja: baseline = kontrole M1 bez `has_bio`; nieregularyzowany logit (własny Newton);
  `GroupKFold(shuffle=True, random_state=SEED)`; bootstrap po nadawcach przez wagi krotności na
  predykcjach out-of-fold.

## D-H3a-16 M4: definicje bramki [default agenta]
- Decyzja: lejek liczony na pełnej próbie głównej (po Hyderabad i complete-case). „≥ 5 swipe'ów po
  każdej stronie” = co najmniej 5 swipe'ów na odbiorcę przy `has_bio = 0` i 5 przy `has_bio = 1`
  (po wykluczeniu swipe'ów z dnia zmiany statusu bio i przypisanych do `first_version`). Przy
  przejściu bramki estymacja tylko na odbiorcach, którzy ją przeszli.
- Wynik: 17 odbiorców < 30, bramka nie przechodzi; M4 nie estymowane (§6 promptu).

## D-H3a-17 S1 [default agenta]
- Decyzja: nadawcy z ≥ 10 swipe'ami w próbie głównej i odsetkiem prawych w (0, 1). Liczby kont
  skrajnych przeliczone po filtrze Hyderabad (w `results.json`, `s1_counts`).

## D-H3a-18 S7 bez `profile_completeness` [default agenta]
- Decyzja: w modelu rozszerzonym `profile_completeness` pominięte.
- Uzasadnienie: jest dokładną kombinacją liniową wskaźników „brak danych” 7 pól, które S7 zawiera.

## D-H3a-19 S8 [default agenta]
- Decyzja: warstwa O tylko przy ≥ 30 nadawcach i ≥ 100 prawych swipe'ach; test interakcji = łączny
  test Walda (χ², df = 2) dla `has_bio × płeć nadawcy` (M, O; referencja F) w pooled logit z
  klastrowaniem dwukierunkowym.

## D-H3a-20 Sanity check GLMM [default agenta]
- Decyzja: symulacja półparametryczna na rzeczywistym designie (X, nadawcy, odbiorcy próby
  głównej): β_bio = 0,15, wyraz wolny −1,8, pozostałe β = 0, σ²_nadawca = 1,5, σ²_odbiorca = 0,5;
  20 powtórzeń na pełnych danych (3 w smoke teście). Raport: obciążenie, SD empiryczne vs średni
  SE, pokrycie 95% CI, wariancje.

## D-H3a-21 Prywatność wyników [default agenta]
- Decyzja: próg 5 dotyczy liczby różnych użytkowników za komórką (dla F1 minimum z nadawców i
  odbiorców; dla F2 odbiorców w koszu; dla F5 odbiorców w oknie ±5 znaków; dla F6 odbiorców w
  etapie lejka). Wytłumione komórki: `NaN` + `suppressed = True`; dokładna mała liczność też
  ukryta. Współczynniki modeli traktowane jako agregaty.

## D-H3a-22 Wykresy opisowe [default agenta]
- Decyzja: F2 na poziomie swipe'ów (ekspozycje, wersja as-of), F1 z 95% CI z bootstrapu po
  odbiorcach, B = 1000.

## D-H3a-23 Kontrola zgodności z kartą: dwie wersje bio
- Decyzja: liczby bio z karty liczono na bieżącym `users`; tabela kontroli podaje obie wersje
  (as-of i bieżące `users`), odchylenie liczone dla as-of.

## D-H3a-24 Cross-check lme4 pominięty
- Decyzja: brak `Rscript` w środowisku → krok pominięty i zapisany (`lme4.status = skipped`).
  Kod ścieżki z R jest w `analysis.lme4_crosscheck`, ale nie był testowany.
- Źródło: prompt §9.

## D-H3a-25 Timeout i cache [default agenta]
- Decyzja: każdy fit GLMM w osobnym procesie (`spawn`) z limitem `FIT_TIMEOUT_MIN`; wyniki
  (tylko agregaty) w `reports/h3a/cache/*.json` z odciskiem danych (hash), więc wznowienie nie
  powtarza fitów; wyniki smoke testów w `reports/h3a_smoke/` (poza gitem).

## D-H3a-26 Pełny przebieg: M1 bez SE, fallback na M2
- Stan: na pełnych danych optymalizacja GLMM zbiega (status 0 w 3 z 4 prób), ale GPBoost nie
  liczy SE współczynników (numeryczny Hessian nie PD) w żadnej próbie; to samo w M5 (M1) i w
  refitach S1, S3, S4, S7 oraz w 8 z 20 replikacji symulacji. Punktowo β_bio = 0,130 (M2: 0,122).
- Decyzja: zgodnie z §6 promptu M2 przejmuje rolę modelu głównego, bez twierdzenia o kontroli
  popularności; etykieta końcowa ma adnotację „fallback”. Nic nie zmieniono po zobaczeniu wyników.
- Do decyzji Dominika: inny sposób uzyskania SE dla GLMM (np. `lme4::glmer` w R albo parametryczny
  bootstrap) wymaga jawnej zmiany planu.
- Źródło: prompt §6.

## D-H3a-27 S7 w M3 bez oszacowania
- Stan: logit z FE nadawcy w modelu rozszerzonym nie zbiega (wartości nieskończone po 200
  iteracjach), prawdopodobnie przez quasi-separację wskaźników pól stylu życia w obrębie nadawców.
  S7 raportowane tylko z M2 (M3 nie wchodzi do reguły werdyktu).

## D-H3a-28 Poziom 3: zakres i status analiz [default agenta]
- Data: 2026-11-03. Zakres: prompt `docs/prompts/h3a-level3-prompt.md` (A1-A5, B1-B3, C, D).
- Decyzja: reguła werdyktu, margines 0,10 i lista S1-S8 bez zmian; etykieta z poziomu 2 nie
  jest nadpisywana. Cały blok A to **diagnostyka post hoc, zainicjowana wynikiem S2a** (poza
  interakcją po płci, zaplanowaną jako S8), bez poprawek na wielokrotność i bez twierdzeń
  potwierdzających. Nie stratyfikowano po żadnej zmiennej liczonej z `y_right`.

## D-H3a-29 Kosze „wieku” konta i profilu [default agenta]
- Kosze ustalone z góry: 0, 1-7, ≥ 8 dni (dzień swipe'a minus dzień pierwszej wersji profilu
  użytkownika). 467 swipe'ów datowanych **przed** pierwszą wersją nadawcy (wiek ujemny) wchodzi do
  kosza 0 (to swipe'y `first_version`). 758 swipe'ów (9 użytkowników bez historii) wyłączone z A2.
- Uwaga: dla nadawcy kosz 0 jest tożsamy z `asof_source = first_version` (42 382 swipe'y), więc
  „pochodzenie cech” i „dzień konta nadawcy” nie są rozróżnialne po stronie nadawcy.

## D-H3a-30 A1: β z prób GPBoost bliżej M2 niż M3 (anomalia wobec oczekiwania)
- Wynik: wszystkie 4 konfiguracje dają β_has_bio = 0,129-0,133 (3 z kodem zbieżności 0, jedna z
  kodem 2: 0,130), wariancja nadawcy 7,6-7,8, odbiorcy 0,56. M2: 0,122, M3: 0,173. Oczekiwanie z
  promptu (β bliżej M3 przy wariancji nadawcy ≈ 7,8) **nie potwierdziło się**; punkt 0,130 z poziomu 2
  jest reprezentatywny. W żadnej próbie GPBoost nie podał SE.

## D-H3a-31 A2: diagnoza S2a (post hoc)
- Wynik: OR (M2) w `prior_version` 1,06 (0,97-1,17), w dopełnieniu 1,21 (1,10-1,34); interakcja
  has_bio × prior: p = 0,081 (M2), 0,069 (M3). Wiek konta nadawcy: kosz 0: 1,22 / 1-7: 1,06 / ≥ 8: 1,10
  (M2), interakcja p = 0,086 (M2), 0,121 (M3). Wiek profilu odbiorcy: brak sygnału (p = 0,34 / 0,93).
  Wniosek: słabszy efekt w S2a jest zgodny z koncentracją efektu w swipe'ach z dnia założenia konta
  nadawcy, ale żaden test interakcji nie przekracza progu 0,05; M3 zachowuje OR > 1 w obu koszach
  z oszacowaniem. Nie zmienia to etykiety; adnotacja: „wrażliwy na skład próby wg dnia konta”.
- M3 bez oszacowania (status `failed`) dla kosza nadawcy ≥ 8 oraz koszy 0 i 1-7 odbiorcy
  (prawdopodobnie quasi-separacja po ograniczeniu próby).

## D-H3a-32 B1: LRT i profil wiarygodności w GPBoost [default agenta]
- `GPModel.fit(offset=...)` jest obsługiwany (GPBoost 1.8), więc β_bio wprowadzono jako offset i
  policzono profil na siatce 11 punktów (±0,25 wokół oszacowania), CI z progu χ² (spline sześcienny).
- Do reguły dodano `classify_interval` (ta sama logika jak `classify`, dla przedziałów innych niż
  Wald). Wynik: LRT χ² = 6,83, p = 0,0089; CI 95% dla β: 0,033-0,227 (OR 1,03-1,25); etykieta
  „potwierdzony”. Log-likelihood to przybliżenie Laplace'a.

## D-H3a-33 B2: `lme4` przez CSV w katalogu tymczasowym; kontrola M1 = M2
- Zmieniono `analysis.lme4_crosscheck` (bez `arrow`; CSV w `tempfile` z uprawnieniami 0700,
  kody całkowite, usuwany po zakończeniu; test jednostkowy na symulacji). R i `lme4` 1.1.35.1 były
  dostępne (poprawka do D-H3a-24).
- Wynik: β = 0,124, SE = 0,049, OR 1,132 (95% CI 1,028-1,247), LRT p = 0,009, wariancje nadawcy 7,43
  i odbiorcy 0,557, kod zbieżności 0, bez osobliwości i ostrzeżeń R. Etykieta „potwierdzony” =
  etykieta M2, więc **reguła zgodności M1 = M2 jest spełniona** (dla M1 = lme4 i dla profilu GPBoost).
  Kontrola estymatora GPBoost vs lme4: β 0,130-0,133 vs 0,124, wariancje zgodne (brak rozbieżności).
- Etykieta końcowa z poziomu 2 pozostaje; po poziomie 3 jej adnotacja „fallback” przestaje być
  konieczna merytorycznie, ale decyzję o zmianie brzmienia pozostawiono Dominikowi.

## D-H3a-34 A5: M3 przeliczone na p.p. [default agenta]
- M3 (FE nadawcy) nie ma populacyjnego efektu krańcowego; do figury C β z M3 przeliczono na p.p.
  przy ryzykach bazowych z M2 (`has_bio = 0`). CI z granic β (bez niepewności ryzyka bazowego).
  Wskazano to w podpisach. Warstwa „inna płeć” pominięta (jak w S8).

## D-H3a-35 Figury A-C: motyw i pas ±1,5 p.p. [default agenta]
- Czcionka: Plus Jakarta Sans z `reports/assets/fonts` (lokalna, już w repo). Okabe-Ito:
  szary #6B7280, niebieski #0072B2, pomarańcz #D55E00; tekst akcentowy #B34F00 (kontrast 5,2:1, bo
  #D55E00 ma 3,9:1). Pas „praktycznie zero” ±1,5 p.p. to wizualny odpowiednik marginesu 0,10
  log-OR przy bazie ≈ 20% (0,2·0,8·0,10 ≈ 1,6 p.p.), nie nowe kryterium.

## Wybór estymatora do obrony ustnej (szkic do akceptacji Dominika)

Model główny to GLMM ze skrzyżowanymi losowymi wyrazami wolnymi nadawcy i odbiorcy; GPBoost daje
tylko oszacowanie punktowe (β ≈ 0,13), więc wnioskowanie opiera się na `lme4` (β = 0,124, OR 1,13,
95% CI 1,03-1,25) i na teście ilorazu wiarygodności (p = 0,009); oba zgadzają się z M2. M2 (pooled
logit, klastrowanie dwukierunkowe) to druga noga reguły zgodności, a M3 (FE nadawcy) kontroluje
hojność nadawcy: M2 i M3 mają inne estymandy (populacyjny vs w obrębie nadawcy), co przy dużej
wariancji nadawcy (≈ 7,5) tłumaczy OR 1,13 vs 1,19.

## D-H3a-36 (2026-11-10, post hoc (audyt)) Etykieta M2 względem reguły; ocena post hoc
- Reguła z sekcji 7 **bez zmian**. M2: OR 1,130, 95% CI 1,044-1,222, 90% CI 1,058-1,207. `equiv`
  fałszywe (górna granica 90% CI 1,207 > exp(0,10) = 1,105), `sig_pos` prawdziwe (dolna granica
  95% CI > 0) → „potwierdzony”. Etykieta wynika z reguły, nie z błędu implementacji.
- Ocena post hoc: reguła porównuje dolną granicę 95% CI z zerem, nie z marginesem, więc
  „potwierdzony” znaczy „różny od zera”, a nie „większy niż pomijalny”. Dolna granica (1,044) leży
  wewnątrz pasma pomijalności. Oryginalna etykieta zostaje; w summary jest flaga.

## D-H3a-37 (2026-11-10, post hoc (audyt)) lme4 jako raportowany M1
- GPBoost nie policzył SE (3/4 prób zbieżnych), więc raportowanym M1 jest `lme4::glmer`
  (crossed (1|sender) + (1|receiver), nAGQ = 0, bobyqa, CI Walda): β = 0,124, SE = 0,049,
  OR 1,132 (95% CI 1,028-1,247; 90% CI 1,044-1,228), LRT p = 0,009, bez osobliwości. GPBoost: tylko
  punkt (OR 1,139). Etykieta wg oryginalnej reguły dla M1 = lme4: „potwierdzony”.
- Niespójność w summary: „lme4: nie uruchomiony” to pole `verdict.lme4` zapisane przed krokiem
  lme4 (nieaktualne); „wrażliwy na estymator (lme4: potwierdzony)” było błędnym porównaniem lme4 z
  etykietą M1 = „brak oszacowania”. Poprawka w `summary.py`: gdy M1 bez SE, lme4 porównujemy z M2.

## D-H3a-38 (2026-11-10, post hoc (audyt)) Scenariusze Z3-Z5 (dodatkowe, nie wchodzą do reguły)
- Z3: has_bio osobno dla nadawców F, M, O (eksploracyjnie, bez korekty wielokrotności).
- Z4: odbiorcy ze stałym tekstem bio (1068 z 1359; 291 ze zmianą, 128 ze zmianą pusty↔niepusty);
  scenariusz bez odbiorców ze zmianą statusu; S2a z lme4.
- Z5: kontrole wieku jak w H1, aktywność odbiorcy (log(1 + swipe'y wysłane); proxy potencjalnie
  endogeniczne), słownik tagów v1 (consensus A + scalenia; kategorie B nie wpływają na H3a).
- Fity poza gitem w `data/interim/h3a/cache`; agregaty w `reports/h3a/audit_results.json`.
