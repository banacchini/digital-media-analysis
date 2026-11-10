# H3a: wyniki (generowane automatycznie)

Wygenerowano: 2026-11-10T03:29; poziom przebiegu: 3; SAMPLE_FRAC = 1.0; SEED = 20261102; margines praktycznego zera |log OR| ≤ 0,10.

## Werdykt

**Etykieta końcowa: potwierdzony (fallback: M2 jako model główny, bez kontroli popularności)**

- M1 (GLMM, skrzyżowane efekty losowe): brak oszacowania
- M2 (pooled logit, klastrowanie dwukierunkowe): potwierdzony
- M3 (FE nadawcy, klastrowanie po odbiorcy; poza regułą): potwierdzony
- lme4: ok; etykieta potwierdzony (zgodna z M2: tak)

## Wynik główny (has_bio: bio odbiorcy niepuste vs puste)

| Model | OR (95% CI; 90% CI) | β | SE | p | MDE OR | Etykieta |
|---|---|---|---|---|---|---|
| M1 | – (95% CI –––; 90% CI –––) | – | – | – | – | brak oszacowania |
| M2 | 1,130 (95% CI 1,044–1,222; 90% CI 1,058–1,207) | 0,1221 | 0,0402 | 0,0024 | 1,119 | potwierdzony |
| M3 | 1,189 (95% CI 1,070–1,320; 90% CI 1,088–1,298) | 0,1727 | 0,0536 | 0,0013 | 1,162 | potwierdzony |

**M1 raportowany = lme4** (Wald): OR 1,132 (95% CI 1,028–1,247), etykieta wg oryginalnej reguły: potwierdzony. GPBoost podaje tylko punkt, bez SE.

Średni efekt krańcowy (M2, populacyjny): 1,90 p.p. (95% CI 0,70–3,11 p.p.; SE z klastrowaniem dwukierunkowym, delta method). Dla laika: przy bio odbiorcy prawy swipe zdarza się o ok. 1,9 p.p. częściej (np. ok. 21,9% zamiast 20%), przy OR 1,130 (M2), 1,132 (lme4) i 1,189 (M3, FE nadawcy). Związek, nie efekt przyczynowy: dotyczy obserwowanej ekspozycji (G1); match ≠ najem. Efekt jest niewielki i bliski minimalnemu wykrywalnemu (MDE OR ≈ 1,12), więc oszacowanie może być zawyżone (przekleństwo zwycięzcy).

## Estymator M1: zbieżność i czasy

- **Optymalizacja zbieżna w 3/4 próbach, ale GPBoost nie policzył SE (numeryczny Hessian nie jest dodatnio określony), więc M1 nie ma CI ani etykiety; zadziałał fallback z §6 promptu.** Oszacowanie punktowe z ostatniej próby: β = 0,1304, OR = 1,139 (bez SE, nie do wnioskowania).
- status: not_converged_or_no_se; optymalizator: lbfgs {'delta_rel_conv': 1e-08}; kod zbieżności GPBoost: 2 (0 = zbieżny); iteracje: 27; czas fitu: 8,5 s
- wariancja efektu losowego nadawcy: 7,770 (SE 0,402); odbiorcy: 0,559 (SE 0,033); log-likelihood (Laplace): -27845,5
- próby optymalizatorów: [{'optimizer': 'lbfgs', 'convergence_status': 0, 'time_s': 6.481233358383179}, {'optimizer': 'gradient_descent', 'convergence_status': 0, 'time_s': 31.447845220565796}, {'optimizer': "gradient_descent {'delta_rel_conv': 1e-08}", 'convergence_status': 0, 'time_s': 52.702144622802734}, {'optimizer': "lbfgs {'delta_rel_conv': 1e-08}", 'convergence_status': 2, 'time_s': 8.462459087371826}]
- sanity check (symulacja na rzeczywistym designie, 12/20 fitów OK): β_bio prawdziwe 0,150, średnie 0,159, obciążenie 0,0095; SD empiryczne 0,0524 vs średni SE 0,0452; pokrycie 95% CI 0,92; wariancje 1,460/1,500 (nadawca), 0,500/0,500 (odbiorca)

## Przepływ próby

| krok                                            |   swipes |   prawe |   nadawcy |   odbiorcy |
|:------------------------------------------------|---------:|--------:|----------:|-----------:|
| Swipe'y na profile                              |    95144 |   19495 |      1583 |       1394 |
| Po wykluczeniu Hyderabad (nadawca lub odbiorca) |    94295 |   19363 |      1544 |       1363 |
| Po complete-case (zmienne modelu)               |    93717 |   19325 |      1538 |       1359 |

Hyderabad: 45 kont; usuwa 849 swipe'ów na profile (jako nadawca 669, jako odbiorca 627).

## M5: długość bio (drugorzędne, bez werdyktu)

- M1: OR na podwojenie długości 1,092 (95% CI –––); OR dla sufitu 250 znaków 0,942 (95% CI –––)
- M2: OR na podwojenie długości 1,031 (95% CI 1,004–1,059); OR dla sufitu 250 znaków 0,912 (95% CI 0,689–1,207)

## M6: przyrost predykcyjny (opisowy)

- ΔlogLoss = -2.47e-04 (95% CI -5.07e-04 do -4.21e-06); ΔAUC = 3.43e-03 (95% CI 1.89e-03 do 4.99e-03); AUC baseline 0,633. Wnioskowanie opiera się na regule z sekcji 7, nie na M6.
- ΔAUC-PR = 2.50e-03 (95% CI 5.62e-04 do 4.15e-03); AUC-PR baseline 0,2890, pełny 0,2915; odsetek prawych 0,206 (poziom odniesienia AUC-PR dla losowego klasyfikatora). Bootstrap po nadawcach (B = 1000), predykcje out-of-fold. M6 jest opisowy.

## M4: analiza w obrębie odbiorcy

- lejek: 1359 odbiorców → 291 ze zmianą tekstu bio → 128 ze zmianą pusty↔niepusty → 17 z ≥ 5 swipe'ami po każdej stronie (próg 30); wariant „bez zmian innych pól”: 9.
- **niemożliwe do zmierzenia tym projektem: 17 odbiorców < 30**.

## Analizy wrażliwości S1-S7

| spec   | model   |   n_obs | OR (95% CI)                                    | label             |
|:-------|:--------|--------:|:-----------------------------------------------|:------------------|
| S1     | M1      |   76187 | – (95% CI –––; 90% CI –––)                     | brak oszacowania  |
| S1     | M2      |   76187 | 1,138 (95% CI 1,047–1,238; 90% CI 1,061–1,222) | potwierdzony      |
| S1     | M3      |   76187 | 1,190 (95% CI 1,071–1,322; 90% CI 1,089–1,300) | potwierdzony      |
| S2a    | M2      |   47373 | 1,064 (95% CI 0,972–1,165; 90% CI 0,986–1,148) | nierozstrzygający |
| S2a    | M3      |   47373 | 1,174 (95% CI 1,042–1,322; 90% CI 1,062–1,297) | potwierdzony      |
| S2b    | M2      |   93717 | 1,127 (95% CI 1,042–1,218; 90% CI 1,055–1,203) | potwierdzony      |
| S2b    | M3      |   93717 | 1,172 (95% CI 1,051–1,306; 90% CI 1,070–1,284) | potwierdzony      |
| S3     | M1      |   94566 | – (95% CI –––; 90% CI –––)                     | brak oszacowania  |
| S3     | M2      |   94566 | 1,128 (95% CI 1,043–1,220; 90% CI 1,056–1,204) | potwierdzony      |
| S3     | M3      |   94566 | 1,187 (95% CI 1,069–1,318; 90% CI 1,087–1,296) | potwierdzony      |
| S4     | M1      |   93717 | – (95% CI –––; 90% CI –––)                     | brak oszacowania  |
| S4     | M2      |   93717 | 1,130 (95% CI 1,044–1,223; 90% CI 1,058–1,208) | potwierdzony      |
| S4     | M3      |   93717 | 1,188 (95% CI 1,069–1,319; 90% CI 1,088–1,297) | potwierdzony      |
| S5     | M2      |   93717 | 1,135 (95% CI 1,048–1,229; 90% CI 1,062–1,213) | potwierdzony      |
| S5     | M3      |   93717 | 1,216 (95% CI 1,099–1,347; 90% CI 1,117–1,325) | potwierdzony      |
| S6     | M2      |   93717 | 1,130 (95% CI 1,044–1,223; 90% CI 1,058–1,208) | potwierdzony      |
| S6     | M3      |   93717 | 1,189 (95% CI 1,070–1,320; 90% CI 1,089–1,298) | potwierdzony      |
| S7     | M1      |   93717 | – (95% CI –––; 90% CI –––)                     | brak oszacowania  |
| S7     | M2      |   93717 | 1,123 (95% CI 1,040–1,213; 90% CI 1,053–1,198) | potwierdzony      |
| S7     | M3      |   93717 | – (95% CI –––; 90% CI –––)                     | brak oszacowania  |

Flagi wrażliwości: S1: różne etykiety między estymatorami (brak oszacowania; potwierdzony) | S2a: różne etykiety między estymatorami (nierozstrzygający; potwierdzony) | S3: różne etykiety między estymatorami (brak oszacowania; potwierdzony) | S4: różne etykiety między estymatorami (brak oszacowania; potwierdzony) | S7: różne etykiety między estymatorami (brak oszacowania; potwierdzony) | etykieta M2 inna niż w specyfikacji głównej w: S2a

## S8: płeć nadawcy

- F: M2 1,259 (95% CI 1,133–1,399; 90% CI 1,152–1,376) [potwierdzony]; M3 1,307 (95% CI 1,145–1,493; 90% CI 1,169–1,462) [potwierdzony]
- M: M2 1,031 (95% CI 0,937–1,134; 90% CI 0,951–1,117) [nierozstrzygający]; M3 1,089 (95% CI 0,973–1,218; 90% CI 0,991–1,196) [nierozstrzygający]
- O: pominięte (za mało danych: 28 nadawców, 355 prawych)
- test interakcji has_bio × płeć nadawcy (Wald, df = 2): χ² = 7,82, p = 0,0200

## Kontrola zgodności z kartą M1

| miara                   |    karta |      asof |   odchylenie_pct |   bieżący_users | flaga_>1pct   |
|:------------------------|---------:|----------:|-----------------:|----------------:|:--------------|
| profile_swipes          | 95144    | 95144     |            0     |         nan     | False         |
| right_swipes            | 19495    | 19495     |            0     |         nan     | False         |
| right_share_pct         |    20.49 |    20.49  |           -0     |         nan     | False         |
| swipers                 |  1583    |  1583     |            0     |         nan     | False         |
| users                   |  2065    |  2065     |            0     |         nan     | False         |
| swipes_with_bio         | 52371    | 52297     |           -0.141 |       52371     | False         |
| right_pct_with_bio      |    21.5  |    21.42  |           -0.372 |          21.537 | False         |
| right_pct_without_bio   |    19.2  |    19.355 |            0.807 |          19.208 | False         |
| missing_age_band_swipes |   578    |   578     |            0     |         nan     | False         |

## Decyzje oznaczone [default agenta]

- D-H3a-2 Gałąź `banacchini/h3-notebook` zamiast `h3a-notebook` [default agenta]
- D-H3a-4 Kilka wersji jednego dnia [default agenta]
- D-H3a-5 `asof_source` na poziomie pary [default agenta]
- D-H3a-6 Cztery polskie etykiety tagów spoza mapowania [default agenta]
- D-H3a-8 G18: rozbieżność `bio_length` [default agenta]
- D-H3a-9 GPBoost 1.8: SE, intercept, optymalizatory [default agenta]
- D-H3a-10 Standaryzacja i kategorie referencyjne [default agenta]
- D-H3a-11 Separacja i współliniowość w designie [default agenta]
- D-H3a-12 M2: własna implementacja CGM i AME [default agenta]
- D-H3a-13 M3: logit z FE nadawcy, profilowany Newton [default agenta]
- D-H3a-14 M5: dwie specyfikacje długości [default agenta]
- D-H3a-15 M6 [default agenta]
- D-H3a-16 M4: definicje bramki [default agenta]
- D-H3a-17 S1 [default agenta]
- D-H3a-18 S7 bez `profile_completeness` [default agenta]
- D-H3a-19 S8 [default agenta]
- D-H3a-20 Sanity check GLMM [default agenta]
- D-H3a-21 Prywatność wyników [default agenta]
- D-H3a-22 Wykresy opisowe [default agenta]
- D-H3a-25 Timeout i cache [default agenta]
- D-H3a-28 Poziom 3: zakres i status analiz [default agenta]
- D-H3a-29 Kosze „wieku” konta i profilu [default agenta]
- D-H3a-32 B1: LRT i profil wiarygodności w GPBoost [default agenta]
- D-H3a-34 A5: M3 przeliczone na p.p. [default agenta]
- D-H3a-35 Figury A-C: motyw i pas ±1,5 p.p. [default agenta]

## Audyt po wynikach (post hoc, nie zmienia reguły z sekcji 7)

### Z1. Skąd etykieta „potwierdzony” (M2)

| Krok reguły | Wartość | Wynik |
|---|---|---|
| Oszacowanie OR (β = 0,1221) | 1,130 | |
| 95% CI | 1,044–1,222 | |
| 90% CI | 1,058–1,207 | |
| Margines (OR) | 0,905–1,105 | |
| `equiv`: 90% CI w marginesie | | **nie** (górna granica 1,207 > 1,105) |
| `sig_pos`: dolna granica 95% CI > 0 | | **tak** |
| Etykieta | | **potwierdzony** |

Etykieta wynika z reguły (kod zgodny ze specyfikacją, test jednostkowy). **Flaga:** reguła porównuje z marginesem górną granicę 90% CI, a dolną granicę 95% CI tylko z zerem. Dolna granica OR (1,044) leży wewnątrz marginesu praktycznego zera (do 1,105), więc „potwierdzony” znaczy „różny od zera”, a nie „większy niż pomijalny”. Nie wykluczono efektu bliskiego granicy pomijalności. Etykiety nie zmieniono.

### Z2. M1: lme4 jako raportowany estymator

| Model | OR (95% CI) | 90% CI | p |
|---|---|---|---|
| M1 (lme4, Wald) | 1,132 (1,028–1,247) | 1,044–1,228 | 0,0119 |
| M1 (GPBoost, tylko punkt) | 1,139 (–) | – | – |
| M2 | 1,130 (1,044–1,222) | 1,058–1,207 | 0,0024 |
| M3 | 1,189 (1,070–1,320) | 1,088–1,298 | 0,0013 |

lme4 (nAGQ = 0, bobyqa, CI Walda): wariancja nadawcy 7,433, odbiorcy 0,557; singularność: nie; kod zbieżności 0; ostrzeżenia: 0. Etykieta wg oryginalnej reguły (M1 = lme4): **potwierdzony**. Wcześniejsze „lme4: nie uruchomiony” było polem `verdict.lme4` zapisanym przed krokiem lme4 (nieaktualne), „potwierdzony” pochodzi z faktycznego przebiegu lme4.

### Z3. Heterogeniczność wg płci nadawcy (eksploracyjnie, bez korekty wielokrotności)

| Zakres | Model | N swipe'ów | OR (95% CI) | Etykieta |
|---|---|---|---|---|
| Z3_F | M2 | 50241 | 1,259 (1,133–1,399) | potwierdzony |
| Z3_F | M3 | 50241 | 1,307 (1,145–1,493) | potwierdzony |
| Z3_F | M1_lme4 | 50241 | 1,253 (1,107–1,419) | potwierdzony |
| Z3_M | M2 | 42621 | 1,031 (0,937–1,134) | nierozstrzygający |
| Z3_M | M3 | 42621 | 1,089 (0,973–1,218) | nierozstrzygający |
| Z3_M | M1_lme4 | 42621 | 1,069 (0,956–1,195) | nierozstrzygający |
| Z3_O | M2 | 855 | 1,268 (0,905–1,776) | nierozstrzygający |
Z3_O / M3: brak oszacowania

Test interakcji has_bio × płeć nadawcy: χ² = 7,82, df = 2, p = 0,020. To analiza post hoc, bez nowej hipotezy; przy kilku sprawdzonych podziałach p = 0,020 nie przetrwałoby korekty wielokrotności. Grupa „O” to 28 nadawców: wynik nie do wnioskowania.

### Z4. Stabilność bio i datowanie as-of

Odbiorcy: 1359; ze zmianą tekstu bio: 291; ze stałym tekstem: 1068; ze zmianą pusty↔niepusty: 128.

| Scenariusz | Model | N swipe'ów | OR (95% CI) | Etykieta |
|---|---|---|---|---|
| Z4_stable_text | M2 | 68906 | 1,132 (1,038–1,234) | potwierdzony |
| Z4_stable_text | M3 | 68906 | 1,176 (1,038–1,332) | potwierdzony |
| Z4_stable_text | M1_lme4 | 68906 | 1,193 (1,058–1,345) | potwierdzony |
| Z4_no_status_change | M2 | 82021 | 1,143 (1,053–1,240) | potwierdzony |
| Z4_no_status_change | M3 | 82021 | 1,202 (1,072–1,348) | potwierdzony |
| Z4_no_status_change | M1_lme4 | 82021 | 1,233 (1,104–1,378) | potwierdzony |
| Z4_S2a_prior_version | M2 | 47373 | 1,064 (0,972–1,165) | nierozstrzygający |
| Z4_S2a_prior_version | M3 | 47373 | 1,174 (1,042–1,322) | potwierdzony |
| Z4_S2a_prior_version | M1_lme4 | 47373 | 1,128 (1,002–1,269) | potwierdzony |

Odbiorcy ze stałym bio dają OR zbliżony do wyniku głównego (błąd as-of nie może ich dotyczyć), więc S2a (M2: nierozstrzygający) wygląda na utratę mocy po odcięciu połowy próby, a nie na błąd datowania. Wniosek ostrożny: oszacowanie punktowe M2 w S2a (1,064) jest niższe niż w pozostałych scenariuszach, a M3 i lme4 w S2a są zgodne z wynikiem głównym.

### Z5. Identyfikacja i kontrole

M4 (analiza wewnątrz odbiorcy) jest niewykonalny (17 < 30 odbiorców), więc efekt `has_bio` wynika **wyłącznie z różnic między odbiorcami** (między-profilowych), nie ze zmiany bio tej samej osoby.

| Specyfikacja | Model | N swipe'ów | OR (95% CI) | Etykieta |
|---|---|---|---|---|
| Z5_age_h1 | M2 | 93717 | 1,137 (1,051–1,231) | potwierdzony |
| Z5_age_h1 | M3 | 93717 | 1,198 (1,079–1,330) | potwierdzony |
| Z5_age_h1 | M1_lme4 | 93717 | 1,143 (1,038–1,259) | potwierdzony |
| Z5_activity | M2 | 93717 | 1,097 (1,016–1,184) | potwierdzony |
| Z5_activity | M3 | 93717 | 1,121 (1,012–1,241) | potwierdzony |
| Z5_activity | M1_lme4 | 93717 | 1,093 (0,992–1,205) | nierozstrzygający |
| Z5_age_h1_activity | M2 | 93717 | 1,106 (1,024–1,194) | potwierdzony |
| Z5_age_h1_activity | M3 | 93717 | 1,130 (1,021–1,251) | potwierdzony |
| Z5_age_h1_activity | M1_lme4 | 93717 | 1,105 (1,002–1,218) | potwierdzony |
| Z5_tags_v1 | M2 | 93717 | 1,130 (1,044–1,223) | potwierdzony |
| Z5_tags_v1 | M3 | 93717 | 1,188 (1,069–1,320) | potwierdzony |
| Z5_tags_v1 | M1_lme4 | 93717 | 1,132 (1,028–1,247) | potwierdzony |

Aktywność = log(1 + liczba swipe'ów odbiorcy jako nadawcy); to proxy potencjalnie endogeniczne (aktywni użytkownicy częściej piszą bio). Wiek „jak w H1” = same_band, age_band_diff_abs, age_band_diff. Zmienne tagów zależą od słownika: po przejściu na słownik v1 zmienia się liczba tagów w 10,3% swipe'ów (średnia 7,52 → 7,42), `tag_cap` w 6307 wierszach, `tag_zero` bez zmian; OR `has_bio` w Z5_tags_v1 jest praktycznie identyczny z głównym.

### Z8. Zmienne jakości bio (opisowo, bez werdyktu)

Wśród swipe'ów na profile z bio (N = 51555): emoji w 18,3%, znak `?` w 0,2%; język (heurystyka stop-słów, **nieprzetestowana**): pl 84,4%, en 5,5%, inny/niejasny 10,1%. Model wtórny w stylu M5 (M2, bez werdyktu):

| Człon | Model | OR (95% CI) | p |
|---|---|---|---|
| log1p_bio_len | bez zmiennych jakości | 1,045 (1,006–1,086) | 0,0233 |
| log1p_bio_len | ze zmiennymi jakości | 1,033 (0,975–1,093) | 0,2702 |
| bio_len_cap | bez zmiennych jakości | 0,912 (0,689–1,207) | 0,5197 |
| bio_len_cap | ze zmiennymi jakości | 0,919 (0,688–1,229) | 0,5694 |
| log1p_emoji | ze zmiennymi jakości | 1,058 (0,933–1,198) | 0,3790 |
| log1p_question | ze zmiennymi jakości | 1,307 (0,452–3,774) | 0,6212 |
| lang_pl | ze zmiennymi jakości | 1,051 (0,876–1,262) | 0,5933 |
| lang_en | ze zmiennymi jakości | 0,900 (0,694–1,167) | 0,4253 |


## Ograniczenia, które muszą towarzyszyć wynikowi

- Związek ≠ przyczynowość: wynik opisuje współwystępowanie bio i prawego swipe'a w obserwowanej ekspozycji, nie efekt napisania bio.
- Brak zdjęć: popularność odbiorcy jest kontrolowana tylko jako efekt losowy (M1); założenie niezależności efektu losowego od has_bio jest wątłe (zdjęcia i staranność profilu mogą iść w parze).
- Ekspozycja przez feed: nie znamy algorytmu rankingu i filtrów; kto komu się wyświetla, może zależeć od profilu (także od bio).
- Czas tylko w dniach: wersja profilu przypisana regułą as-of (D7); swipe'y z dnia zmiany są przypisane do wersji sprzed dnia.
- Próba samoselekcyjna i jednorodna (studenci, głównie 18-20 lat, kilka miast); brak uogólnienia na wszystkich szukających współlokatora. Match ≠ najem.
- Pola stylu życia mają duże braki (74-81% w 5 z 7 pól); `profile_completeness` jest więc grubą miarą staranności profilu.
- Mapowanie tagów (`interests_mapping.csv`) nie jest zrecenzowane przez człowieka; liczba tagów jest prowizoryczna (stąd S6).
- Brak identyfikacji wewnątrz odbiorcy (M4: 17 < 30 odbiorców): efekt has_bio wynika wyłącznie z różnic między odbiorcami.
- Kontrola aktywności odbiorcy (liczba swipe'ów jako nadawcy) jest potencjalnie endogeniczna.
- Widoczność bio na karcie profilu: informacja od Dominika, brak potwierdzenia dostawcy.
