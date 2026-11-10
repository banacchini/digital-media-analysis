# H2: podsumowanie wyników (po audycie 2026-11-10)

**Hipoteza H2 (karta M1, w wersji D17):** płeć (i wiek) nadawcy i odbiorcy wpływają na prawy swipe.
Formułujemy ją jako **oszacowanie wielkości efektu**, nie test bramki. **Status: eksploracyjna**, bo
macierz płci widzieliśmy przed sformułowaniem hipotezy.

**Wniosek (eksploracyjny): prawy swipe przewidują głównie para płci i wiek odbiorcy względem nadawcy; ocena jest
warunkowa na ekspozycji.** To zachowanie w aplikacji wśród profili pokazanych przez feed (G1): korelacja, nie
preferencja ani przyczyna.

Szczegóły: `notebooks/h2_demographics.ipynb` (sekcja 7), `docs/h2/audit-fixes-2026-11-10.md` (co i dlaczego
zmieniono), `docs/h2/open-questions.md`.

## 1. Co zbadaliśmy

Jednostka: skierowany swipe A→B na profil, wynik `y_right`. Płeć i wiek z wersji profilu z dnia swipe'a (D7),
bez Hyderabadu (D10). Próba: 94 295 swipe'ów; model płci (bez `O`, G16) 91 598; model wieku 93 717.

## 2. Dwa estymatory i które OR są które

- **pooled** (populacyjny): regresja logistyczna, SE klastrowane po nadawcy i odbiorcy. OR opisuje przeciętną parę.
- **GLMM** (warunkowy): crossed random intercepts nadawcy i odbiorcy. OR opisuje tę samą parę nadawca-odbiorca.
  Wariancja efektu nadawcy ok. 7,5 (SD ok. 2,7 logitu) sprawia, że OR GLMM są **znacznie dalej od 1**. Nie porównujemy OR z
  różnych estymatorów bez tego zastrzeżenia. SE: `lme4`, a gdy GPBoost je zwrócił (Z1 z kontrolami), GPBoost.
- GLMM ma za wąskie CI dla efektów zależnych od nadawcy (brak losowych nachyleń); dla `h` ufamy szerszemu pooled.

## 3. Wyniki

**Płeć.** Odsetki prawych: F→F 20,0%, F→M 8,5%, M→F 29,6%, M→M 19,9%. Profile kobiet dostają więcej prawych
swipe'ów od obu grup nadawców (kobiety +11,5 p.p. wobec kobiet niż mężczyzn; mężczyźni +9,7 p.p. wobec kobiet niż
mężczyzn). Rozdzielenie „popularności profili kobiet" `π` i „premii za własną płeć" `h` jest możliwe **tylko przy
założeniu** symetrii (jedna wartość dla obu płci nadawców); bez założeń identyfikowany jest tylko iloraz luk
`exp(2h)`. Osobnych `h_F`, `h_M` nie raportujemy.

**Wiek.** Nadawcy 18–20: 20,5% prawych dla tego samego pasma, 13,7% / 9,5% / 6,6% dla odbiorców o 1 / 2 / 3 pasma
starszych. Jest **kara za starszego odbiorcę**, a nie preferencja podobnego wieku (młodszy odbiorca i to samo pasmo
bez wyraźnego efektu). Zgodne z H1; różnica OR względem H1 wynika z kontroli płci i miasta.

**Poza próbą.** Płeć + wiek: AUC 0,63 (nowy nadawca) i 0,64 (nowy odbiorca); wiek dodaje do samej płci mało,
ale mierzalnie (sparowany bootstrap).

## 4. Tablica dowodów

Wszystkie liczby w `notebooks/h2_demographics.ipynb`, komórka „Liczby do wniosku". 95% CI.

| # | Twierdzenie | Liczba | Estymator | Status |
|---|---|---|---|---|
| E1 | Profile kobiet dostają więcej prawych swipe'ów od obu płci nadawców | F→F 20,0% [17,4; 23,0], F→M 8,5% [6,2; 11,1], M→F 29,6% [24,8; 34,5], M→M 19,9% [16,2; 24,0] | bootstrap po nadawcach | eksploracyjne (macierz widziana przed H2) |
| E2 | OR ta sama vs inna płeć, nadawcy F / M | 2,645 [2,063; 3,390] / 0,602 [0,498; 0,729]; z kontrolami wiek i miasto 2,439 [1,909; 3,116] / 0,657 [0,541; 0,799] | pooled | pre-rejestrowane (karta M1) |
| E3 | Iloraz luk „odbiorca F vs M" u nadawców F i M, `exp(2h)` (bez założeń) | 1,59 [1,16; 2,18]; GLMM 1,93 [1,73; 2,16] | pooled; GLMM (lme4) | post hoc (audyt) |
| E4 | Popularność profili kobiet `π`, przy symetrii | OR 2,13 [1,81; 2,51]; GLMM 3,91 [3,47; 4,39]; z kontrolami (pooled) 1,91 [1,63; 2,25] | pooled; GLMM | post hoc (audyt) |
| E5 | Premia za własną płeć `h`, przy symetrii | OR 1,26 [1,08; 1,48]; GLMM 1,39 [1,32; 1,47]; z kontrolami (pooled) 1,25 [1,07; 1,47] | pooled; GLMM (CI za wąskie) | post hoc (audyt) |
| E6 | Starszy odbiorca zmniejsza szansę (na pasmo różnicy) | pooled FE pasma 0,69 [0,61; 0,77]; bez FE 0,58 [0,47; 0,72]; GLMM 0,49 [0,44; 0,53] | pooled; GLMM (lme4) | specyfikacja pre-rejestrowana; FE post hoc |
| E7 | Młodszy odbiorca i to samo pasmo bez wyraźnego efektu | młodszy: pooled 0,96 [0,86; 1,07], GLMM 0,92 [0,84; 1,01]; to samo pasmo: pooled 1,03 [0,90; 1,17], GLMM 1,00 [0,89; 1,11] | pooled; GLMM | j.w. |
| E8 | Spójność z H1 | starszy o 1: 0,62 [0,57; 0,68] (H1) → 0,67 [0,59; 0,74] (kontrole płci i miasto, klastry dwukierunkowe); o 2+: 0,36 → 0,41 [0,33; 0,50]; młodszy o 1: 0,97 → 0,92 [0,82; 1,04] | pooled (dummies, FE pasma) | post hoc (audyt) |
| E9 | Przewidywanie poza próbą, nowy nadawca | AUC płeć 0,59 [0,56; 0,62]; płeć + wiek 0,63 [0,60; 0,66]; AUC-PR 0,29 [0,25; 0,33] (baza 0,21) | OOF zbiorczo, bootstrap po nadawcach | eksploracyjne |
| E10 | Przewidywanie poza próbą, nowy odbiorca | AUC płeć 0,61 [0,59; 0,64]; płeć + wiek 0,64 [0,61; 0,67] | j.w. | post hoc (audyt) |
| E11 | Wiek dodaje do samej płci (nowy nadawca / nowy odbiorca) | Δ log loss −0,0045 [−0,0078; −0,0010] / −0,0058 [−0,0090; −0,0025]; ΔAUC +0,035 [0,018; 0,053] / +0,029 [0,016; 0,042] | sparowany bootstrap po nadawcach | post hoc (audyt) |

## 5. Co jest konfirmacyjne, eksploracyjne, post hoc

- **Konfirmacyjne:** nic (H2 eksploracyjne, D17).
- **Pre-rejestrowane w karcie M1:** OR ta sama vs inna płeć według płci nadawcy (E2), model z `\|Δwiek\|` i `Δwiek` ze znakiem (E6, E7), 6 scenariuszy wrażliwości (notebook 6.2), foldy po nadawcach.
- **Post hoc (audyt):** E3–E5 (dekompozycja i założenie), GLMM (lme4), FE nadawcy, macierz wieku, FE pasma, most do H1 (E8), AUC-PR, foldy po odbiorcach, bootstrap różnic (E10–E11), blok `sex+age3`.

## 6. Ograniczenia

- **Ekspozycja (G1):** widzimy tylko pary pokazane przez feed; ocena warunkowa na ekspozycji.
- **Korelacja, nie preferencja:** `π` i `h` to etykiety przy założeniu symetrii, a `receiver_F` jest skorelowane z innymi cechami odbiorcy.
- **GLMM:** brak losowych nachyleń, więc CI efektów zależnych od nadawcy są za wąskie (Q3); źródła GLMM mieszane (lme4 i GPBoost, Q4).
- **Płeć `O`** jest mała i często powstaje przez zmianę płci (G8, G16); wiek tylko jako pasmo i dominuje 18–20 (G13); próba wąska (G6).
- **As-of (D7):** ok. połowa swipe'ów ma cechy z pierwszej wersji profilu; wpływu nie oszacowano (Z5 pominięte, Q11).
- **`y_match`** (Z6) nie był analizowany. Prawy swipe to nie decyzja o wspólnym wynajmie (G9).
