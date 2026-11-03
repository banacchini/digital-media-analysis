# H3a, poziom 3: diagnostyka, błędy standardowe GLMM, figury (generowane)

Wygenerowano: 2026-11-03T02:29.

## 1. Co zmienia się względem poziomu 2

- Etykieta z poziomu 2 pozostaje: **potwierdzony (fallback: M2 jako model główny, bez kontroli popularności)**. Reguła werdyktu, margines 0,10 i lista S1-S8 bez zmian.
- Nowe: dla M1 (GLMM) są teraz błędy standardowe i CI z dwóch niezależnych źródeł (sekcja 3), więc reguła zgodności M1 = M2 mogła zostać sprawdzona.
- Adnotacja do S2a: efekt w połowie próby z `prior_version` jest słabszy (sekcja 2, A2).

## 2. Blok A (diagnostyka post hoc, zainicjowana wynikiem S2a; bez poprawek na wielokrotność; S8 była zaplanowana)

### A1. Wszystkie próby optymalizatora GPBoost (specyfikacja główna)

| konfiguracja | kod zbieżności | β has_bio | wariancja nadawcy | wariancja odbiorcy | log-lik. | czas [s] |
|---|---|---|---|---|---|---|
| lbfgs | 0 | 0,1328 | 7,75 | 0,564 | −27 845,6 | 3,0 |
| gradient_descent | 0 | 0,1292 | 7,57 | 0,556 | −27 846,2 | 34,2 |
| gradient_descent {'delta_rel_conv': 1e-08} | 0 | 0,1299 | 7,74 | 0,560 | −27 845,5 | 56,7 |
| lbfgs {'delta_rel_conv': 1e-08} | 2 | 0,1304 | 7,77 | 0,559 | −27 845,5 | 5,0 |

β zbieżnych prób: 0,1292 do 0,1328; M2: 0,1221, M3: 0,1727. Oszacowanie GLMM jest bliższe M2. Oczekiwanie z promptu (β bliżej M3 przy wariancji nadawcy ≈ 7,8) nie potwierdziło się; zapisano jako anomalię w decision-logu. Żadna próba nie dała SE dla współczynników.

### A2. Heterogeniczność wg pochodzenia cech i „wieku” konta (diagnoza S2a)

| wymiar | grupa | model | OR (95% CI) | n swipe'ów | etykieta |
|---|---|---|---|---|---|
| asof | prior_version | M2 | 1,06 (0,97–1,16) | 47 373 | nierozstrzygający |
| asof | prior_version | M3 | 1,17 (1,04–1,32) | 47 373 | potwierdzony |
| asof | first_version / users_current | M2 | 1,21 (1,10–1,34) | 46 344 | potwierdzony |
| asof | first_version / users_current | M3 | 1,32 (1,17–1,49) | 46 344 | potwierdzony |
| wiek_nadawca | 0 | M2 | 1,22 (1,10–1,36) | 42 415 | potwierdzony |
| wiek_nadawca | 0 | M3 | 1,42 (1,25–1,62) | 42 415 | potwierdzony |
| wiek_nadawca | 1-7 | M2 | 1,06 (0,95–1,19) | 24 333 | nierozstrzygający |
| wiek_nadawca | 1-7 | M3 | 1,24 (1,07–1,42) | 24 333 | potwierdzony |
| wiek_nadawca | ≥ 8 | M2 | 1,10 (0,99–1,22) | 26 211 | nierozstrzygający |
| wiek_nadawca | ≥ 8 | M3 | brak oszacowania | 26 211 | brak oszacowania |
| wiek_odbiorca | 0 | M2 | 1,01 (0,86–1,18) | 5 482 | nierozstrzygający |
| wiek_odbiorca | 0 | M3 | brak oszacowania | 5 482 | brak oszacowania |
| wiek_odbiorca | 1-7 | M2 | 1,06 (0,94–1,18) | 27 453 | nierozstrzygający |
| wiek_odbiorca | 1-7 | M3 | brak oszacowania | 27 453 | brak oszacowania |
| wiek_odbiorca | ≥ 8 | M2 | 1,15 (1,04–1,27) | 60 024 | potwierdzony |
| wiek_odbiorca | ≥ 8 | M3 | 1,16 (1,02–1,31) | 60 024 | potwierdzony |

| interakcja z has_bio | model | χ² Walda | df | p |
|---|---|---|---|---|
| pochodzenie cech (prior_version × has_bio) | M2 | 3,05 | 1 | 0,081 |
| pochodzenie cech (prior_version × has_bio) | M3 | 3,30 | 1 | 0,069 |
| dzień konta nadawcy (kosze 0 / 1-7 / ≥ 8) | M2 | 4,91 | 2 | 0,086 |
| dzień konta nadawcy (kosze 0 / 1-7 / ≥ 8) | M3 | 4,22 | 2 | 0,121 |
| wiek profilu odbiorcy (kosze 0 / 1-7 / ≥ 8) | M2 | 2,18 | 2 | 0,336 |
| wiek profilu odbiorcy (kosze 0 / 1-7 / ≥ 8) | M3 | 0,15 | 2 | 0,928 |

Wyłączone z analiz wieku: 758 swipe'ów, 9 użytkowników bez historii profilu.

### A3. Stabilność OR po dodawaniu kontroli

| krok | model | OR (95% CI) |
|---|---|---|
| samo bio | M2 | 1,140 (1,044–1,245) |
| samo bio | M3 | 1,218 (1,086–1,367) |
| + płeć, wiek, miasto pary | M2 | 1,118 (1,033–1,211) |
| + płeć, wiek, miasto pary | M3 | 1,209 (1,090–1,340) |
| + kompletność profilu | M2 | 1,140 (1,052–1,234) |
| + kompletność profilu | M3 | 1,204 (1,084–1,337) |
| + liczba zainteresowań (model główny) | M2 | 1,130 (1,044–1,222) |
| + liczba zainteresowań (model główny) | M3 | 1,189 (1,070–1,320) |

### A4. E-value (przybliżenie RR ≈ √OR)

| grupa | model | OR | E-value punktu | E-value granicy CI |
|---|---|---|---|---|
| wszyscy | M2 | 1,130 | 1,32 | 1,17 |
| wszyscy | M3 | 1,189 | 1,40 | 1,22 |
| kobiety | M2 | 1,259 | 1,49 | 1,33 |
| kobiety | M3 | 1,307 | 1,55 | 1,34 |
| mężczyźni | M2 | 1,031 | 1,14 | 1,00 |
| mężczyźni | M3 | 1,089 | 1,26 | 1,00 |

Założenia: wynik częsty (baza ≈ 20%), `E = RR + √(RR(RR−1))`. To miara czułości, nie dowód braku konfundowania; E-value 1,00 oznacza przedział obejmujący 1.

### A5. Prawdopodobieństwa standaryzowane i średni efekt krańcowy (M2)

| warstwa | bez bio | z bio | różnica w p.p. (95% CI) | na 100 swipe'ów |
|---|---|---|---|---|
| wszyscy | 19,6% | 21,5% | 1,90 (0,70 do 3,11) | 19,6 → 21,5 |
| kobiety | 14,4% | 17,3% | 2,95 (1,62 do 4,29) | 14,4 → 17,3 |
| mężczyźni | 25,4% | 26,0% | 0,56 (−1,19 do 2,32) | 25,4 → 26,0 |

Warstwa „inna płeć” pominięta (za mało danych, jak w S8).

| spec | opis | AME M2 [p.p.] | 95% CI | M3 przeliczone [p.p.] |
|---|---|---|---|---|
| main | model podstawowy | 1,90 | 0,70 do 3,11 | 2,73 |
| S1 | tylko aktywni użytkownicy | 2,22 | 0,80 do 3,64 | 3,00 |
| S2a | tylko swipe'y z pewną wersją profilu | 0,91 | −0,39 do 2,21 | 2,41 |
| S2b | cechy z aktualnych profili | 1,87 | 0,67 do 3,07 | 2,51 |
| S3 | z kontami z Hyderabadu | 1,87 | 0,67 do 3,07 | 2,71 |
| S4 | inna miara kompletności profilu | 1,91 | 0,70 do 3,11 | 2,71 |
| S5 | bio < 10 znaków uznane za puste | 1,98 | 0,75 do 3,20 | 3,11 |
| S6 | surowa liczba zainteresowań | 1,91 | 0,70 do 3,11 | 2,73 |
| S7 | więcej cech profilu w modelu | 1,81 | 0,62 do 2,99 | – |
| S8_F | tylko kobiety oceniają | 2,95 | 1,62 do 4,29 | 3,48 |
| S8_M | tylko mężczyźni oceniają | 0,56 | −1,19 do 2,32 | 1,59 |

M3 (FE nadawcy) nie ma efektu krańcowego w populacji; kolumna „przeliczone” stosuje β z M3 do ryzyk bazowych z M2 (szacunek orientacyjny, CI z granic β).

## 3. Blok B: błędy standardowe dla GLMM (M1)

| szczebel | co uzyskano | β | SE lub p | CI | status |
|---|---|---|---|---|---|
| B1 LRT (GPBoost) | test istotności (nie równoważności) | 0,1328 | p = 0,0089 | – | χ² = 6,83 |
| B1 profil wiarygodności | CI z profilu | 0,1328 | – | 95%: 0,033 do 0,227 | potwierdzony |
| B2 lme4 (Wald) | β, SE, CI Walda | 0,1240 | SE = 0,0493 | 95% OR: 1,028–1,247 | potwierdzony |

- Reguła zgodności M1 = M2 (GPBoost (profil)): M1 **potwierdzony**, M2 **potwierdzony** → **zgodne**.
- Reguła zgodności M1 = M2 (lme4): M1 **potwierdzony**, M2 **potwierdzony** → **zgodne**.
- lme4: wariancja nadawcy 7,43, odbiorcy 0,557; osobliwość: False; kod zbieżności: 0; ostrzeżenia R: 0; czas 29 s.
- Kontrola estymatora (GPBoost vs lme4): β 0,1328 vs 0,1240; wariancje nadawcy 7,75 vs 7,43, odbiorcy 0,564 vs 0,557; brak rozbieżności.

Uwaga: M2 i M1 mają inny estymand (efekt populacyjny vs warunkowy na efekty losowe), co przy dużej wariancji nadawcy tłumaczy różnice rzędu 0,01-0,05 w β.

## 4. Pliki w `reports/h3a/export/`

- `h3a_captions.md`
- `h3a_fig_A.png`
- `h3a_fig_A.svg`
- `h3a_fig_A_preview.png`
- `h3a_fig_B.png`
- `h3a_fig_B.svg`
- `h3a_fig_B_preview.png`
- `h3a_fig_C.png`
- `h3a_fig_C.svg`
- `h3a_fig_C_preview.png`
- `h3a_numbers.json`
- `theme.json`
