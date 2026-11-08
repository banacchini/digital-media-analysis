# Prompt dla agenta Claude Code: notebook analizy H3a (RentFriends)

Zapisz ten plik jako `docs/prompts/h3a-notebook-prompt.md` i podaj agentowi jego ścieżkę.
Autor decyzji: Dominik Czech (lead badawczy; cała praca nad H3a jest jego). Data: 2026-11-02.

---

## 0. Rola i cel

Jesteś agentem analitycznym w repozytorium projektu *Analiza Mediów Cyfrowych, RentFriends*.
Przygotuj **parametryzowany notebook (i moduł w `src/rentfriends/`) z pełną analizą hipotezy H3a**,
uruchamialny bezobsługowo (papermill), który po około 3 godzinach daje zestaw wyników
wystarczający do decyzji „co jeszcze trzeba zrobić”. Najpierw budujesz i testujesz na próbie,
potem **zatrzymujesz się i raportujesz** (sekcja 12). Pełnego przebiegu nie uruchamiasz bez zgody.

Miarą sukcesu jest rzetelny wniosek o zakresie i pewności odpowiadających dowodom, nie „ładny wynik”.
Wynik zerowy lub nierozstrzygający jest pełnoprawnym rezultatem (zasady kursu).

## 1. Hipoteza H3a i to, co ją obala

- **Pytanie:** czy staranność bio odbiorcy (profilu B) jest związana z prawym swipe'em A→B
  **ponad** kompletność profilu odbiorcy, liczbę jego tagów i demografię pary?
- **H3a:** istnieje dodatni związek `has_bio` → `y_right` po tych kontrolach.
- **Zakres:** tylko H3a (pusty/niepusty + długość). **H3b (treść bio, embeddingi, NLP) jest poza
  zakresem: nie ładuj modeli językowych, nie licz podobieństwa tekstów.**
- Wnioski mają dotyczyć **związku**, nie przyczynowości. Match ≠ najem. Bio jest widoczne dla
  użytkowników na karcie profilu (informacja od Dominika, nie od dostawcy).

## 2. Twarde zasady (nie podlegają negocjacji)

1. **Prywatność / data statement:** publikowalne są wyłącznie wyniki zagregowane.
   Nigdy nie wypisuj ani nie zapisuj: tekstu bio, `user_key`, tabel na poziomie wiersza
   (w outputach notebooka, logach, CSV, wykresach). Do plików wynikowych tylko agregaty;
   komórki o liczności < 5 użytkowników tłumisz (`NaN` + flaga `suppressed`).
2. **Bez zewnętrznych API i usług.** Bio przetwarzane tylko lokalnie. `bio_len` liczysz z tekstu
   lokalnie i zapisujesz tylko liczbę. Audyt PII bio jest nieukończony, więc nie wyświetlaj tekstu
   nawet „na próbę”.
3. **Nie edytuj** `codebook.md`, karty M1, data statement ani dokumentu technicznego.
   Propozycje zmian kodebooka idą do osobnego pliku (sekcja 11).
4. **Powtarzalność:** `SEED = 20261102`, wersje pakietów zapisane do `reports/h3a/env.txt`.
5. **Brak cichych decyzji:** jeśli coś jest niejednoznaczne, wybierz domyślną opcję z tego pliku
   lub (gdy brak) najbardziej zachowawczą, zapisz w `docs/h3a/decision-log.md` jako
   `D-H3a-n [default agenta]` i wypisz w raporcie z sekcji 12. Sprzeczność między tym plikiem a
   dokumentami repo zgłaszasz, nie rozstrzygasz po cichu.
6. **Git:** pracuj na gałęzi `h3a-notebook`, małe logiczne commity z opisowymi komunikatami
   (commity są oceniane), bez `push`. Konwencje z `AGENTS.md` mają pierwszeństwo.
7. **Logi sesji agenta** zachowaj zgodnie z konwencją repo (`logs/ai/`), nie usuwaj ich.
   Dopisz wpis do `docs/ai-disclosure.md` w istniejącym formacie (agent, zadanie, data, ścieżka
   tego promptu, osoba recenzująca: Dominik Czech). Nie przepisuj cudzych wpisów.
8. GPU (RTX 5060) nie jest potrzebne. Nie instaluj ciężkich zależności CUDA.

## 3. Pliki do przeczytania na początku (znajdź je w repo)

`AGENTS.md` (setup, polecenia, konwencje); `docs/rentfriends_hipotezy_karta_eksploracji.md`
(G1-G18, sekcje o dawnym H5 = obecne H3); karta M1 (PDF, jeśli jest w repo);
`codebook.md` (Część C: definicje zmiennych); `data-statement.md`; `docs/prompts/m1-generation-plan.md`
(decyzje D1-D22, w tym **D7: reguła wersji profilu**); `docs/ai-disclosure.md`;
`interests_mapping.csv` (124 surowe → 67 kanonicznych tagów); notebooki `notebooks/EDA*.ipynb`,
`users_overview`, `profile_history_overview`; `src/rentfriends/`; katalog `data/processed/`.

**Uwaga:** codebook powołuje się na „as-of rule from section 0”, której nie ma w pliku. Regułę
bierz z D7 i z §5 karty (poniżej). Zgłoś tę lukę w raporcie.

**Zanim cokolwiek zbudujesz**, sprawdź, co już istnieje (tabela cech as-of, filtr Hyderabad,
funkcje wczytujące dane, helpery wykresów). **Używaj istniejących artefaktów**; brakujące buduj
minimalnie w `src/rentfriends/h3a/` w tych samych konwencjach.

## 4. Dane, jednostka analizy, próba

- **Jednostka:** swipe A→B na **profil** (`swipes.target_type = 'profile'`), `y_right = (direction == 'right')`.
- **Próba główna:** wszyscy swipujący, **bez progu aktywności i bez wykluczania kont skrajnych**;
  **wykluczone 45 kont z Hyderabad** (jako nadawca lub odbiorca; policz i zaraportuj ile swipe'ów
  to usuwa i czy D-decyzje w planie M1 mówią inaczej).
- **Cechy as-of (obie strony pary):** ostatnia wersja profilu **sprzed dnia swipe'a** (`prior_version`);
  dla swipe'ów z dnia pierwszej wersji lub wcześniejszych: wersja 1 (`first_version`);
  dla 9 użytkowników bez historii: bieżące `users` (`users_current`). Zapisuj kolumnę `asof_source`.
  Nie ufaj `changed_fields` dla płci i miasta (G17); zmiany wykrywaj porównaniem snapshotów.
- **Dane brakujące w zmiennych modelu:** complete-case na zmiennych modelu; policz i zaraportuj
  utratę (karta: 578 swipe'ów bez `age_band`). `age_band` 27+ połączone (D9).
- **Tabela przepływu próby** (attrition): 95 144 swipe'y na profile → po filtrze Hyderabad → po
  complete-case. Zapisz jako tabelę i wykres (F0).
- **Kontrola zgodności z kartą** (liczby są przed filtrem Hyderabad i przed wersjonowaniem, więc
  różnice są oczekiwane, ale muszą być wyjaśnione): 95 144 swipe'y na profile, 19 495 prawych (20,49%),
  1583 swipujących z 2065, 52 371 swipe'ów na profile z bio (21,5% prawych vs 19,2% bez bio, surowo).
  Odchylenia powyżej ~1% zgłoś.

## 5. Zmienne

Nazwy zgodne z codebookiem, tam gdzie istnieją. Zmienne nowe trafiają do addendum (sekcja 11).

| Zmienna | Definicja |
|---|---|
| `y_right` | 1 jeśli A swipe'ował B w prawo |
| `bio_empty` | 1 jeśli bio odbiorcy (as-of) jest NULL lub po `strip()` ma długość 0 |
| `has_bio` | `1 - bio_empty`. **W modelach używaj `has_bio`**, żeby OR > 1 wspierał hipotezę |
| `bio_empty_alt10` | wariant: puste także gdy po `strip()` < 10 znaków (S5) |
| `bio_len` | długość w znakach **liczona z tekstu** (G18), nie z `bio_length`. Zaraportuj odsetek rozbieżności z `bio_length` |
| `bio_len_cap` | 1 jeśli `bio_len >= 250` (sufit pola) |
| `sex_pair` | płeć nadawcy × odbiorcy, `O` jako osobna kategoria (9 komórek). **Bez `same_sex`** (redundantne) |
| `age_band_diff`, `same_band` | numer pasma odbiorcy minus nadawcy (ze znakiem), to samo pasmo; 27+ połączone |
| `same_city` | to samo / inne / nieznane (dla „inne”) |
| `profile_completeness` | odsetek niepustych spośród 7 pól stylu życia odbiorcy (as-of) |
| `profile_completeness_alt` | to samo bez `cleanliness` i `noise_level` (mianownik 5; możliwe wartości domyślne) (S4) |
| `tag_count_receiver` | liczba efektywnych tagów odbiorcy po mapowaniu z `interests_mapping.csv` i deduplikacji; w modelu: liczba liniowo + flaga `==0` + flaga `==9` (sufit) |
| `tag_count_raw` | surowa liczba tagów (S6) |
| `receiver_age_band` | pasmo wieku odbiorcy (tylko modele rozszerzone, S7) |

Mapowanie tagów nie jest jeszcze zrecenzowane przez człowieka: liczba tagów jest prowizoryczna
(stąd S6). Rozbieżności w repo (67 kanonicznych w mapowaniu vs 69 w codebooku; slugi `bussiness`,
`often_outside` w `tag_category_proposal.csv` nieobecne w mapowaniu) nie wpływają na H3a, ale je zgłoś.

## 6. Modele

**M1 (główny): GLMM, GPBoost.**
`y_right ~ has_bio + sex_pair + age_band_diff + same_band + same_city + profile_completeness + tag_count_receiver (+flagi)`
ze skrzyżowanymi losowymi wyrazami wolnymi nadawcy i odbiorcy.
- `gpb.GPModel(group_data=np.column_stack([sender, receiver]), likelihood="bernoulli_logit")`,
  `fit(y=y, X=X, params={"std_dev": True})`. Sprawdź w dokumentacji, czy trzeba jawnie dodać
  kolumnę interceptu do `X` i jak sprawdzić zbieżność. Zmienne ciągłe standaryzuj dla stabilności.
- **Najpierw sanity check** na danych symulowanych (znany OR, skrzyżowane efekty losowe, rozmiar
  zbliżony do danych): estymator ma odtworzyć parametry. Kilka minut, wynik do raportu.
- Przy braku zbieżności: inny optymalizator wg dokumentacji GPBoost; jeśli nadal nie, fallback z karty
  (M2 jako model główny, **bez twierdzenia o kontroli popularności**) i wyraźna adnotacja.
- Raportuj: `beta`, `SE`, OR (dla `has_bio`) z **95% i 90% CI** (Wald, SE przybliżone, Laplace),
  wariancje efektów losowych, log-likelihood, czas fitu.

**M2: pooled logit, klastrowanie dwukierunkowe (nadawca, odbiorca).** `statsmodels`
(`cov_type='cluster'` z dwiema kolumnami grup; zweryfikuj, że to faktycznie dwukierunkowe, w razie
potrzeby zaimplementuj Cameron-Gelbach-Miller). Raportuj też **średni efekt krańcowy w p.p.**
(populacyjny; zweryfikuj, że macierz kowariancji w `get_margeff` jest klastrowana, inaczej delta method ręcznie).

**M3: logit z efektami stałymi nadawcy, SE klastrowane po odbiorcy.** Wycina hojność nadawcy
bez GLMM; nadawcy z samymi 0 lub 1 odpadają. Wybierz implementację (rzadkie dummies albo
`ConditionalLogit`), zachowując klastrowanie po odbiorcy; opisz wybór.

**M4: analiza w obrębie odbiorcy (drugorzędna, z bramką wykonalności).**
- Status bio odbiorcy w czasie ze snapshotów `profile_history` (porównanie tekstu/emptiness między
  kolejnymi wersjami, bez użycia `changed_fields`). Pomiń swipe'y z dnia zmiany statusu bio oraz
  swipe'y przypisane do `first_version` (status niepewny).
- **Bramka:** zgłoś lejek (F6): odbiorcy ze zmianą bio → ze zmianą statusu pusty↔niepusty → z ≥ 5
  swipe'ami po każdej stronie po wykluczeniach. **Jeśli < 30 odbiorców, nie estymuj**; raportuj
  „niemożliwe do zmierzenia tym projektem” razem z liczbami.
- Jeśli bramka przechodzi: LPM (p.p.) z efektami stałymi odbiorcy i tygodnia (`day // 7`),
  SE klastrowane po odbiorcy; towarzysząco FE-logit, jeśli wykonalny. Wariant: tylko zmiany, w
  których inne pola profilu się nie zmieniły (porównanie snapshotów), jeśli liczność pozwala.
  Interpretuj ostrożnie (dni, skład nadawców, zmiany rankingu feedu).

**M5: długość bio (wynik drugorzędny, bez etykiety werdyktu).** Podpróba `has_bio == 1`;
`log1p(bio_len)` + spline (3 df) + `bio_len_cap`, te same kontrole co M1. Raportuj efekt na
podwojenie długości (OR z CI) i krzywą dose-response. **Bez progów praktycznej istotności**
(margines z sekcji 7 dotyczy tylko `has_bio`).

**M6: przyrost predykcyjny (opisowy).** `GroupKFold` po nadawcy (5 foldów), pooled logit bez
efektów losowych: baseline vs baseline + `has_bio`. ΔlogLoss i ΔAUC z CI z bootstrapu po nadawcach
(B = 1000, na predykcjach out-of-fold). Oznacz wyraźnie jako opisowy; wnioskowanie opiera się na sekcji 7.

## 7. Kryterium rozstrzygnięcia (ustalone z góry, nie zmieniać po zobaczeniu wyników)

Margines „praktycznie zero”: |log OR| ≤ **0,10** (OR ≈ 0,90-1,11; przy bazie 20% ok. ±1,5 p.p.).
Implementuj jako czystą funkcję `classify(beta, se, margin=0.10)` z testami jednostkowymi.

- `equiv`: 90% CI w całości w [-0,10; 0,10] (TOST, α = 0,05)
- `sig_pos`: dolna granica 95% CI > 0; `sig_neg`: górna granica 95% CI < 0

Etykieta (kolejność ma znaczenie):
1. `equiv` → **„praktycznie zero”** (dopisz „istotnie dodatni/ujemny”, jeśli 95% CI wyklucza 0)
2. `sig_pos` → **„potwierdzony”**
3. `sig_neg` → **„efekt przeciwny do hipotezy”**
4. w przeciwnym razie → **„nierozstrzygający”**

**Reguła zgodności:** etykieta z M1 (GLMM) musi być identyczna z etykietą z M2 (pooled logit,
klastrowanie dwukierunkowe). Jeśli nie, końcowa etykieta to **„wrażliwy na specyfikację”** z oboma
wynikami. Jeśli cross-check `lme4` (poziom 2) daje inną etykietę, dopisz **„wrażliwy na estymator”**.
M3 raportujesz obok, bez udziału w regule. Raportuj też **minimalny wykrywalny OR**
(`exp(2,80 * SE)`, moc 80%, α = 0,05) z M1 i M2.

## 8. Analizy wrażliwości

Każda z S1-S8 przechodzi przez M2 i M3 (sekundy). GLMM (M1) refitujesz **tylko** dla S1, S3, S4, S7 (poziom 2).

| ID | Definicja |
|---|---|
| S1 | nadawcy z ≥ 10 swipe'ami i bez kont skrajnych (18 z samymi prawymi, 359 z samymi lewymi) |
| S2 | (a) tylko swipe'y z `asof_source == prior_version`; (b) cechy z bieżącego `users` na wszystkich swipe'ach |
| S3 | z kontami Hyderabad |
| S4 | `profile_completeness_alt` zamiast `profile_completeness` |
| S5 | `bio_empty_alt10` |
| S6 | `tag_count_raw` zamiast zmapowanej |
| S7 | model rozszerzony: baseline + `receiver_age_band` + wartości 7 pól stylu życia odbiorcy (kategorie z poziomem „brak danych”) |
| S8 | stratyfikacja po płci nadawcy (F, M; O tylko jeśli liczności pozwalają) + test interakcji `has_bio × płeć nadawcy` (pooled logit, klastrowane SE) |

## 9. Budżet czasu i przebieg

Parametry w pierwszej komórce (papermill): `RUN_LEVEL` (1 lub 2), `SAMPLE_FRAC` (domyślnie 1.0),
`SAMPLE_BY="sender"`, `SEED`, `MARGIN=0.10`, `FIT_TIMEOUT_MIN=90`, `REPORT_DIR="reports/h3a"`.

- **Poziom 1 (cel ok. 3 h, kończy się automatycznym podsumowaniem):** dane i as-of, opisówka,
  F0-F2, M1 + M2 + M3 + etykieta + MDE, M5, M6, M4 (bramka, a przy jej przejściu estymacja),
  szybkie wersje S1-S8, `summary.md`.
- **Poziom 2 (bez nadzoru, może iść przez noc):** refity GLMM dla S1, S3, S4, S7; cross-check
  `lme4` na specyfikacji głównej (patrz niżej), aktualizacja F3 i `summary.md`.
- **Timeout pojedynczego fitu: 90 min.** Po przekroczeniu zapisz status `timeout` i idź dalej; nie
  upraszczaj specyfikacji po cichu.
- **Cache wyników** każdego modelu na dysku (JSON z agregatami: współczynniki, SE, CI, czas, status),
  żeby wznowienie nie powtarzało fitów. Loguj czas każdego kroku do `reports/h3a/timings.csv`.
- **Cross-check `lme4`:** tylko jeśli są `Rscript`, `lme4` i `arrow`. `glmer(..., family = binomial, nAGQ = 0)`
  ze skrzyżowanymi `(1|sender) + (1|receiver)`, wymiana danych przez parquet w katalogu tymczasowym
  (usuń po zakończeniu), ta sama specyfikacja co M1, timeout. Brak R/pakietów → pomiń i zapisz.
- **Skrypt uruchomieniowy:** `scripts/run_h3a.sh` (papermill, `nohup`, log do `reports/h3a/run.log`)
  i krótka instrukcja w `docs/h3a/README.md`.
- Całość notebooka ma działać też z `SAMPLE_FRAC=0.1` w ≤ 10 minut (smoke test).

## 10. Wykresy i tabele: zapis poza notebookiem

Cel: z wyników da się bez pracy ręcznej złożyć prezentację i plakat.

1. Każdy wykres zapisuj **osobnymi plikami** w `reports/h3a/figures/` jako **PNG (300 dpi) i SVG**
   (SVG do PowerPointa/plakatu), nazwa `h3a_<nn>_<slug>.png|svg`. Notebook dodatkowo wyświetla je inline.
2. Dla każdego wykresu zapisz **dane źródłowe (zagregowane)** w `reports/h3a/figure_data/h3a_<nn>_<slug>.csv`
   (z zastosowaniem tłumienia komórek < 5), by dało się go przerysować.
3. Jedna funkcja `save_fig(fig, name, data_df)` w `src/rentfriends/h3a/figs.py` zapisuje PNG + SVG + CSV
   i dopisuje wiersz do `reports/h3a/figures_manifest.csv`
   (plik, proponowany podpis po polsku, model/specyfikacja, N swipe'ów i odbiorców, wersja z datą).
4. **Styl pod slajdy 16:9:** jeden moduł stylu, rozmiar ok. 10 × 5,6 cala, czcionka osi ≥ 14 pt,
   paleta bezpieczna dla daltonistów, krótki tytuł, opisane osie z jednostkami, legenda w obrębie
   wykresu, **niepewność widoczna** (CI), bez dekoracji. Etykiety po polsku.
5. Tabele wynikowe zapisuj jako CSV **i** Markdown w `reports/h3a/tables/`
   (m.in. tabela głównego wyniku, tabela wrażliwości, przepływ próby).

Wykresy:

| ID | Treść |
|---|---|
| F0 | przepływ próby (lejek swipe'ów) |
| F1 | odsetek prawych swipe'ów wg `has_bio` i płci nadawcy, z CI (bootstrap po odbiorcach); opisowo, bez kontroli |
| F2 | rozkład `bio_len` wśród niepustych (histogram, sufit 250 zaznaczony) + odsetek pustych |
| F3 | **wykres główny:** forest plot OR dla `has_bio` w M1, M2, M3, lme4 (jeśli jest), S1-S8; słupki 95% i 90% CI, pas marginesu praktycznego zera [e^-0,10; e^0,10], linia OR = 1 |
| F4 | stratyfikacja po płci nadawcy (OR z CI) + wynik testu interakcji |
| F5 | krzywa dose-response długości bio (M5) z pasem CI i oznaczonym sufitem |
| F6 | lejek bramki wykonalności M4 (a przy jej przejściu: współczynnik w obrębie odbiorcy) |
| F7 | przyrost predykcyjny: ΔlogLoss i ΔAUC z CI |
| F8 | balans kontroli między `has_bio = 1` i `0` (standaryzowane różnice średnich) |

## 11. Dokumentacja i artefakty (wszystko krótkie, w języku polskim, identyfikatory po angielsku)

- `docs/h3a/decision-log.md`: dziennik `D-H3a-n` (data, decyzja, uzasadnienie, odrzucone alternatywy,
  źródło: ten prompt albo [default agenta]). Na końcu sekcja **„Wybór estymatora do obrony ustnej”**
  (2-3 zdania: dlaczego GLMM ze skrzyżowanymi efektami jako model główny, czemu pooled logit z
  klastrowaniem i FE nadawcy jako kontrole, i co przy braku zbieżności).
- `docs/codebook_addendum_h3a.md`: wiersze w formacie Części C codebooka dla nowych zmiennych
  (`tag_count_receiver`, `bio_empty_alt10`, `receiver_age_band`, `bio_len_cap`,
  `profile_completeness_alt`, `tag_count_raw`) oraz uwagi (np. `same_sex` redundantne z `sex_pair`).
  Nie edytuj `codebook.md`.
- `reports/h3a/summary.md` (generowany automatycznie na końcu poziomu 1 i 2): etykieta werdyktu,
  OR z CI dla M1/M2/M3, MDE, AME w p.p., status zbieżności i czasy, wynik bramki M4 (i estymacja,
  jeśli była), wyniki S1-S8 w jednej tabeli, flagi „wrażliwy na specyfikację/estymator”,
  lista `D-H3a` oznaczonych [default agenta], oraz blok **„Ograniczenia, które muszą towarzyszyć
  wynikowi”**: związek ≠ przyczynowość; brak zdjęć (popularność tylko jako efekt losowy,
  założenie niezależności od `has_bio` jest wątłe); ekspozycja przez feed; czas tylko w dniach;
  próba samoselekcyjna i jednorodna (studenci, 18-20); pola stylu życia z dużymi brakami;
  mapowanie tagów niezrecenzowane; bio widoczne wg Dominika (brak potwierdzenia dostawcy).
- Logika w `src/rentfriends/h3a/` (wczytanie i as-of, zmienne, modele, `classify`, `save_fig`),
  notebook `notebooks/H3a.ipynb` cienki (wywołania + opis); wersja z wynikami jako
  `notebooks/H3a-rendered.ipynb` (konwencja jak przy EDA; outputy tylko zagregowane).
- Minimalne testy `pytest`: `classify` (przypadki brzegowe etykiet), definicja `bio_empty`
  (NULL, spacje, jeden znak), przypisanie as-of (przed pierwszą wersją, dzień zmiany, brak historii),
  tłumienie komórek < 5.
- Nowe zależności (co najmniej `gpboost`) dopisz do pliku zależności zgodnie z `AGENTS.md` i wymień w raporcie.

## 12. Punkt zatrzymania i raport (po smoke teście na `SAMPLE_FRAC=0.1`)

Zatrzymaj się i przedstaw Dominikowi (zwięźle, technicznie, tylko zagregowane liczby):
1. Czy notebook przechodzi end-to-end na próbie i ile trwał każdy krok (`timings.csv`);
   **ekstrapolacja czasu pełnego fitu GPBoost** i szacunek całkowitego czasu poziomu 1 i 2.
2. Wynik sanity checku GPBoost na danych symulowanych.
3. Stan zbieżności M1 na próbie i ewentualne problemy z estymatorem.
4. **Liczby bramki M4 policzone na pełnych danych** (wymaga tylko `profile_history`, jest tanie).
5. Tabela przepływu próby na pełnych danych, kontrola zgodności z kartą i wszystkie odchylenia.
6. Lista decyzji `D-H3a` oznaczonych [default agenta] oraz znalezione niespójności w dokumentach
   (sekcja 0 codebooka, liczba tagów 67/69, slugi) i brakujące artefakty, które zbudowałeś lokalnie.
7. Polecenie uruchomienia poziomu 1 w tle i szacowany czas.

Po zgodzie Dominika: poziom 1 → `summary.md` → (poziom 2 na noc).

## 13. Czego nie robić

- Nie wprowadzaj H3b, embeddingów, ekstrakcji sygnałów z bio ani modeli językowych.
- Nie zmieniaj marginesu 0,10, reguł etykiet ani listy S1-S8 po zobaczeniu wyników (zmiany tylko
  jako jawny wpis w decision-log z uzasadnieniem i zgodą Dominika).
- Nie rozszerzaj analiz o match, rozmowy ani H1/H2.
- Nie wyświetlaj ani nie zapisuj danych wierszowych, `user_key` ani tekstu bio.
