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

## Wybór estymatora do obrony ustnej

Model główny to GLMM ze skrzyżowanymi losowymi wyrazami wolnymi nadawcy i odbiorcy, bo ten sam
użytkownik występuje w wielu parach w obu rolach: losowy wyraz nadawcy wchłania jego „hojność”,
a odbiorcy jego popularność (w tym niezmierzone cechy, np. zdjęcia), więc `has_bio` jest
porównywane przy tej samej ogólnej atrakcyjności profilu, o ile jest od niej niezależne. Pooled
logit z błędami klastrowanymi dwukierunkowo nie modeluje popularności, ale daje odporne SE bez
założeń o rozkładzie efektów losowych i jest drugą nogą reguły zgodności; logit z FE nadawcy
usuwa hojność nadawcy bez założenia niezależności od cech. Przy braku zbieżności GLMM wynik
główny przejmuje M2 z adnotacją, że nie kontroluje popularności odbiorcy.
