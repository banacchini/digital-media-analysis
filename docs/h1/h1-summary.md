# H1: podsumowanie wyników (po rebase na kontrakt danych v1)

**Hipoteza H1:** zgodność stylu życia przewiduje prawy swipe silniej niż zgodność wieku i zainteresowań.

**Werdykt: H1 niepotwierdzona.** **Demografia wygrywa, deklarowane dopasowanie dodaje niewiele.** Kryterium z karty M1 jest spełnione w kierunku przeciwnym: najsilniej prawy swipe przewiduje wiek (jako kierunek: kara za starszego odbiorcę), a styl życia i zainteresowania dodają niewiele (udział wieku w sumie ΔLL: 90,6% [70,8; 96,0]). Który z dwóch słabych bloków, styl życia czy zainteresowania, wnosi więcej, **pozostaje nierozstrzygnięte** i zależy od klasyfikacji tagów. Badamy prawy swipe w aplikacji, a nie faktyczny najem, i opisujemy związki, nie przyczyny.

Szczegóły: `notebooks/h1-hypothesis-rendered.ipynb` (sekcja 11 ma tablicę dowodów E1–E14), `docs/h1/rebase-v1-2026-11-09.md` (co się zmieniło względem v0), `docs/data-contract-v1.md`, `docs/h1/d15-conflict-investigation.md`, `docs/h1/audit-fixes-2026-11-08.md`, `docs/h1/open-questions.md`.

**Co się zmieniło w tej wersji.** Liczby liczymy teraz na kontrakcie danych **v1**, zbudowanym z końcowych decyzji walidacji tagów (konsensus A + B + scalenia tagów; jeden recenzent, jedna runda). Poprzednie liczby (mapowanie agenta) nazywamy **v0** i podajemy obok. Formalny werdykt się nie zmienia; zmienia się to, co możemy powiedzieć o stylu życia wobec zainteresowań (sekcja 4.4) i dochodzą dwie sekcje: wrażliwość na słownik tagów (4.5) oraz anomalia D15 (4.6).

---

## 1. Co zbadaliśmy

**Pytanie:** czy to, że dwie osoby mają zgodny styl życia (pora snu, palenie, hałas, czystość, praca zdalna, alkohol i tagi stylu życia), pomaga przewidzieć, że A przesunie profil B w prawo, bardziej niż zgodność wieku i wspólne zainteresowania?

**Intuicja:** przy wspólnym mieszkaniu liczą się codzienne nawyki bardziej niż wspólne hobby czy podobny wiek.

**Jednostka analizy:** jeden skierowany swipe A→B na profil; wynik `y_right` (1 = prawy).

**Próba główna:** 92 754 swipe'y (1525 nadawców, 1354 odbiorców; 20,7% prawych), ta sama w v0 i v1. Lejek: 116 414 wszystkich swipe'ów → 95 144 na profile → 94 295 po wykluczeniu kont z Hyderabadu → 93 717 ze znanym wiekiem obu stron (próba H2/H3a) → 92 754 z co najmniej jednym wspólnie znanym polem stylu życia (próba H1).

## 2. W jaki sposób

- **Cechy z dnia swipe'a**, nie z bieżącego profilu (reguła as-of, D7); tagi stylu życia uzupełniają braki pól strukturalnych, a zainteresowania są oczyszczone z tagów stylu życia (D12, D13).
- **Słownik tagów (v1):** mapowanie surowych tagów (konsensus A), kategorie hobby / styl życia (konsensus B) i scalenia tagów z `docs/tag-validation/` (jeden recenzent, nie w pełni ślepy, bez testu powtórnego). v0 używa mapowania i kategorii agenta.
- **Trzy bloki zmiennych**, po 3 zmienne każdy:
  - wiek: ta sama grupa wiekowa, odległość grup, kierunek (odbiorca − nadawca);
  - zainteresowania: Jaccard, liczba wspólnych, różnica liczby tagów;
  - styl życia: odsetek zgodnych pól, konflikt kierunkowy tagów, liczba wspólnych tagów.
- **Identyczne kontrole we wszystkich modelach:** para płci nadawca→odbiorca (8 zmiennych) i miasto.
- **Regresja logistyczna** z błędami klastrowanymi po nadawcy i odbiorcy (ta sama osoba występuje w wielu swipe'ach).
- **Kryterium z karty:** przyrost dopasowania po dodaniu stylu życia vs po dodaniu wieku i zainteresowań, z przedziałem ufności różnicy; przyrosty jako blok pierwszy, ostatni i średnio po wszystkich 6 kolejnościach.
- **Przedziały ufności:** bootstrap klastrowy (1000 powtórzeń, ziarno 42) osobno po nadawcach i po odbiorcach; jako konserwatywny przyjmujemy szerszy. Dla przyrostów bloków i ich stosunku są to percentyle rozkładu bootstrapowego (bez korekty obciążenia), więc są szerokie i asymetryczne.
- **Walidacja poza próbą:** 5 foldów, każdy nadawca w jednym foldzie; logloss, AUC i AUC-PR; sparowane różnice modeli z bootstrapem po nadawcach (1000 powtórzeń).
- **Kontrole dodatkowe:** test tasowania stylu życia między odbiorcami; baseline losowych par dla zainteresowań; analiza każdego z 7 pól stylu życia (korekta Holma); 12 scenariuszy wrażliwości (teraz z CI).

## 3. Dlaczego tak

- Zasady kursu: liczy się **wniosek o zakresie i pewności zgodnych z dowodami**, a nie wynik modelu; dobrze uzasadniony wynik negatywny jest pełnoprawny.
- Użytkownicy powtarzają się w wielu parach, więc błędy i przedziały muszą uwzględniać klastrowanie; foldy muszą być po użytkownikach, by nie było wycieku.
- Bloki mają różną liczbę zmiennych i są skorelowane, stąd obie kolejności dodawania, średnia po kolejnościach i ΔLL na stopień swobody.
- Słownik tagów to ludzka decyzja o niepewnym zakresie, więc sprawdzamy, jak wynik zależy od niej (sekcja 4.5), zamiast zakładać, że v1 jest „prawdą".

## 4. Wyniki

Estymata [95% CI]; kolumny v1 i v0.

### 4.1 Główne: kryterium H1

| Pytanie | v1 | v0 |
|---|---|---|
| Średni przyrost ΔLL: wiek | 533,8 [341,8; 915,4] | 533,2 [340,2; 915,0] |
| Średni przyrost ΔLL: styl życia | 32,6 [8,9; 118,4] | 42,5 [11,0; 135,9] |
| Średni przyrost ΔLL: zainteresowania | 23,1 [4,1; 116,7] | 13,9 [2,3; 101,4] |
| Styl życia − wiek+zainteresowania (ΔLL, ostatni) | **−524,1 [−905,6; −323,4]** | −504,5 [−883,4; −300,8] |
| Styl życia − wiek (ΔLL, ostatni) | −499,2 [−855,9; −276,8] | −487,8 [−845,8; −273,3] |
| Styl życia − zainteresowania (ΔLL, ostatni) | 7,3 [−81,4; 83,0] (nierozstrzygnięte) | 27,0 [−59,3; 106,4] (nierozstrzygnięte) |
| CV, styl życia − wiek+zainteresowania: logloss | −0,0055 [−0,0087; −0,0024] | −0,0053 [−0,0085; −0,0020] |
| CV: AUC | −0,0245 [−0,0353; −0,0133] | −0,0224 [−0,0330; −0,0117] |
| CV: AUC-PR | −0,0309 [−0,0485; −0,0172] | −0,0310 [−0,0488; −0,0166] |

Wniosek jest taki sam dla każdej definicji przyrostu i w każdym z 12 scenariuszy wrażliwości na v1: 22,1–54,1 to ΔLL stylu życia, 357–901 to ΔLL wieku+zainteresowań, a różnica S − WZ jest ujemna z CI bez zera w 12 z 12 scenariuszy (v0: 12 z 12).

### 4.2 Wiek: kierunek, nie podobieństwo (bez zmian; wiek nie zależy od słownika tagów)

Przy efektach stałych grupy wiekowej nadawcy, względem tej samej grupy wiekowej:

| Odbiorca | OR | 95% CI |
|---|---|---|
| młodszy o 1 grupę | 0,97 | [0,87; 1,09] |
| starszy o 1 grupę | 0,62 | [0,57; 0,68] |
| starszy o 2 lub więcej | 0,35 | [0,29; 0,43] |

To jest **kara za starszego odbiorcę**, a nie preferencja podobnego wieku. Po uwzględnieniu odległości i kierunku sama zgodność grupy nie jest istotna (OR 0,78 [0,56; 1,07]).

### 4.3 Styl życia: słaby sygnał, bez zysku poza próbą

- Ponad przypadek: ΔLL 30,3 wobec 5,1 [0,4; 14,7] z tasowania odbiorców (v0: 40,5 wobec 5,1 [0,4; 15,6]); p na minimum rozdzielczości testu.
- Poza próbą jako ostatni blok: AUC 0,0007 [−0,0015; 0,0030], logloss −0,0002 [−0,0008; 0,0004], AUC-PR −0,0022 [−0,0063; 0,0012]. Brak mierzalnej poprawy (v0 bez zmiany wniosku).
- Per pole: **żadne z 7 pól nie przechodzi korekty Holma** (najmniejsze p po Holmie 0,56, `cleanliness`).
- Palenie (eksploracyjnie): niepalący → użytkownik OR 0,86 [0,78; 0,95]; asymetrii kierunku nie wykazano (p = 0,66).

### 4.4 Styl życia vs zainteresowania: nierozstrzygnięte i zależne od klasyfikacji tagów

To zastępuje wcześniejsze twierdzenie „zainteresowania są najsłabsze".

- Stosunek ΔLL stylu życia do zainteresowań: **3,05 [0,27; 26,03]** na v0, 1,71 [0,22; 14,86] dla konsensusu A + B, **1,41 [0,18; 13,18]** na v1. Punktowo spada z 3,05 do 1,4–1,7, ale **przedziały obejmują 1 w każdym wariancie**: dane nie rozstrzygają, co wnosi więcej.
- Różnica ΔLL styl życia − zainteresowania (ostatni): 7,3 [−81,4; 83,0] na v1, 27,0 [−59,3; 106,4] na v0. Znak dodatni, CI obejmuje zero w każdym wariancie słownika.
- W v0 jedyny wynik na korzyść stylu życia nad zainteresowaniami to AUC jako blok *pierwszy*: 0,0075 [0,0017; 0,0137]. Na v1: 0,0032 [−0,0033; 0,0093], CI obejmuje zero. Wynik **nie przetrwał zmiany klasyfikacji** i nie jest wsparciem dla H1.

### 4.5 Wrażliwość na słownik tagów

Klasyfikacja hobby / styl życia pochodzi od **jednego recenzenta** (nie w pełni ślepego, bez testu powtórnego), a granica hobby / styl życia (np. `cooking`, `instruments`) wpływa na wynik porównania bloków.

| Słownik | ΔLL zainteresowania | ΔLL styl życia | stosunek styl życia / zainteresowania |
|---|---|---|---|
| v0 (agent) | 13,9 [2,3; 101,4] | 42,5 [11,0; 135,9] | 3,05 [0,27; 26,03] |
| tylko A | 14,0 [2,3; 101,5] | 42,4 [11,0; 135,3] | 3,04 [0,26; 25,93] |
| tylko B | 23,5 [4,2; 118,1] | 40,5 [11,3; 130,0] | 1,72 [0,22; 14,98] |
| A + B | 23,6 [4,3; 118,4] | 40,4 [11,5; 130,2] | 1,71 [0,22; 14,86] |
| v1 (A + B + scalenia) | 23,1 [4,1; 116,7] | 32,6 [8,9; 118,4] | 1,41 [0,18; 13,18] |

- **Dekompozycja** (jeden refit na każdą decyzję przesuniętą względem v0, ΔΔLL średniego ΔLL bloku zainteresowania / styl życia): `cooking` hobby → styl życia 7,81 / −3,81; `instruments` 2,49 / −0,12; `long_talks` −2,87 / 1,67; `vanlife` −0,26 / 0,07; `city_breaks`, `healthy_food`, `marketing_social`, `tech_it` 0 (ta sama kategoria co w v0); wszystkie scalenia razem −0,41 / −8,41; wszystkie decyzje (v1) 9,16 / −9,92. To liczby, bez interpretacji mechanizmu.
- **Zmiana v1 − v0** (parami, te same losowania): ΔLL zainteresowań 9,2 (po nadawcach [−24,6; 54,4], po odbiorcach [1,0; 17,9]); ΔLL stylu życia −9,9 (po nadawcach [−34,0; 9,9], po odbiorcach [−17,9; −3,5]). Po losowaniu odbiorców zmiana jest wyraźna, po losowaniu nadawców nie; konserwatywnie (szerszy przedział) nie rozstrzygamy, czy jest istotna.
- **Wniosek o wieku jest od słownika niezależny:** udział wieku w sumie ΔLL wynosi 89,3–90,6% w każdym z pięciu wariantów, a kryterium H1 ma ten sam znak i wyklucza zero w każdym.
- Wykres: `reports/h1/rebase/dictionary_sensitivity.png`.
- Scenariusze diagnostyczne z zastępczym kodem pola `lifestyle` uzupełnianym z `often_out` (Z5 walidacji tagów) są **założeniem, nie danymi**, i nie są podstawą żadnego wniosku.

### 4.6 Anomalia D15: 52% swipe'ów z konfliktem tagów stylu życia

Odsetek swipe'ów z konfliktem (jedna strona ma tag z jednej strony grupy polaryzacji, druga z przeciwnej) wynosi 52,4% na v1 (52,3% na v0). To **prawdziwa prewalencja, nie błąd**: odsetek jest równy oczekiwanemu przy niezależności stron (52,5% [52,3; 52,7]), bo tagi stylu życia są bardzo częste (ma je 98,2% nadawców), a w kodzie są **pięć** grup polaryzacji. Zmiennej nie zmieniono, więc nie ma wpływu poprawki na blok stylu życia. Sama definicja (np. grupa palenia dubluje pole `smoking`) czeka na decyzję zespołu (`open-questions.md`, Q13). Szczegóły: `docs/h1/d15-conflict-investigation.md`.

### 4.7 Zainteresowania

Średni Jaccard prawych vs lewych swipe'ów: różnica 0,0049 [−0,0008; 0,0108] na v1 (0,0040 [−0,0021; 0,0101] na v0); IDF-Jaccard 0,0042 [−0,0005; 0,0093]. Po uwzględnieniu klastrowania CI obejmuje zero w obu wariantach.

## 5. Wnioski

1. **H1 niepotwierdzona.** W danych z aplikacji styl życia przewiduje prawy swipe słabiej niż wiek; różnica jest duża i jej CI nie obejmuje zera, w v0 i v1, w każdym wariancie słownika i w każdym z 12 scenariuszy.
2. **Demografia wygrywa.** Prawy swipe przewiduje przede wszystkim to, kto kogo ogląda: para płci i wiek odbiorcy względem nadawcy. AUC poza próbą (zbiorczo, CI po nadawcach): same kontrole 0,605 [0,576; 0,635], kontrole + wiek 0,638 [0,608; 0,669], + styl życia 0,615 [0,588; 0,642], + zainteresowania 0,612 [0,585; 0,638].
3. **Deklarowane dopasowanie dodaje niewiele.** Styl życia i zainteresowania razem to 9,4% [4,0; 29,2] sumy ΔLL.
4. **Styl życia vs zainteresowania pozostaje nierozstrzygnięte**; zależy od klasyfikacji tagów (stosunek 3,05 w v0; 1,41–1,71 w wariantach konsensusu).
5. **Brak mierzalnego efektu nie dowodzi, że styl życia nie ma znaczenia przy wyborze współlokatora.** Dowodzi tylko, że ten pomiar w tym etapie decyzji niewiele dodaje (patrz ograniczenia).

## 6. Ograniczenia

- **Rozdzielczość pomiaru.** Pięć z siedmiu pól stylu życia ma 74–81% braków na poziomie profili; na poziomie par braki u którejkolwiek strony to 47–92% swipe'ów. `cleanliness` i `noise_level` (ok. 2% braków) mogą być wartościami domyślnymi. Wiek jest kompletny, ale gruby (4 grupy). Porównanie bloków zależy więc od jakości pomiaru, nie tylko od realnego związku.
- **Klasyfikacja tagów: jeden recenzent**, nie w pełni ślepy, bez testu powtórnego; granica hobby / styl życia wpływa na porównanie stylu życia z zainteresowaniami (sekcja 4.5). Walidacja nie obejmuje powtórzenia przez drugiego recenzenta.
- **Widoczność cech (hipoteza niezweryfikowana).** Możliwe, że wiek jest dla użytkowników bardziej widoczny niż pola stylu życia. Dane tego nie rozstrzygają (brak zdjęć, nieznana widoczność pól i tagów); to pytanie do dostawcy.
- **Ekspozycja i próba.** Widzimy tylko pary pokazane przez feed; 65% wyświetlanych profili to grupa 18–20; próba jest wąska (studencka).
- **Match i swipe to nie najem.** Wnioski dotyczą prawego swipe'a.
- **Specyfikacja i analizy poprawiane po obejrzeniu wyników** (audyt; walidacja tagów). Dlatego nawet analiza konfirmacyjna ma stopnie swobody badacza; raportujemy wszystkie warianty.
- **Techniczne:** ΔLL na poziomie swipe'a zakłada niezależność obserwacji i zawyża dowód (o kryterium rozstrzygają CI z bootstrapu klastrowego); CI przyrostów ΔLL to percentyle bez korekty obciążenia; CI w CV są warunkowe na dopasowanych modelach foldów; nie użyto modelu z efektami losowymi; 963 swipe'y bez żadnego wspólnie znanego pola stylu życia wypadają z modelu.

## 7. Co jest konfirmacyjne, a co eksploracyjne

| Analiza | Status |
|---|---|
| CI różnicy przyrostów (kryterium karty), CV po użytkownikach, test tasowania | konfirmacyjne (specyfikacja kontroli poprawiona po audycie); przeliczone na v1 |
| Scenariusze D6, D7, G6; kwadrat różnicy wieku; IDF-Jaccard; baseline losowych par | pre-rejestrowana wrażliwość |
| Para płci zamiast `same_sex`, efekty stałe grupy nadawcy, kontrola sufitu 9 tagów | post hoc (audyt), raportowane |
| Rozkład na 3 bloki (Shapley), kierunek wieku, analiza per pole, kierunek palenia | eksploracyjne / post hoc (audyt) |
| Kontrakt v1, wrażliwość na słownik z CI, stosunek styl życia / zainteresowania, dekompozycja tagów, CI przyrostów bloków, 12 scenariuszy z CI, anomalia D15 | **post hoc (walidacja tagów)** |

## 8. Co zmienił rebase na v1

Wniosek formalny „H1 niepotwierdzona" i nagłówek „demografia wygrywa, deklarowane dopasowanie dodaje niewiele" się nie zmieniły. Zmieniło się:
(a) twierdzenie „zainteresowania są najsłabsze" zastąpiono: stosunek ΔLL stylu życia do zainteresowań zależy od słownika tagów, a styl życia vs zainteresowania jest nierozstrzygnięte (z CI);
(b) jedyny wynik na korzyść stylu życia nad zainteresowaniami (AUC jako blok pierwszy) nie przetrwał zmiany klasyfikacji;
(c) dodano ograniczenie: klasyfikacja tagów od jednego recenzenta;
(d) wyjaśniono anomalię D15 (prawdziwa prewalencja).
Poprzednie wersje: `docs/h1/audit-fixes-2026-11-08.md` (audyt, v0).
