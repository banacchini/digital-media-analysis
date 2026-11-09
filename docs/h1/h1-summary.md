# H1: podsumowanie wyników

**Hipoteza H1:** zgodność stylu życia przewiduje prawy swipe silniej niż zgodność wieku i zainteresowań.

**Werdykt: H1 nie została potwierdzona.** Kryterium z karty M1 jest spełnione w kierunku przeciwnym. Najsilniej prawy swipe przewiduje wiek (jako kierunek: kara za starszego odbiorcę). Styl życia daje słaby sygnał bez mierzalnego zysku poza próbą, a zainteresowania są najsłabsze. Badamy prawy swipe w aplikacji, a nie faktyczny najem, i opisujemy związki, nie przyczyny.

Szczegóły: `notebooks/h1-hypothesis-rendered.ipynb` (sekcja 11 ma tablicę dowodów E1–E11), `docs/h1/audit-fixes-2026-11-08.md`, `docs/h1/open-questions.md`.

---

## 1. Co zbadaliśmy

**Pytanie:** czy to, że dwie osoby mają zgodny styl życia (pora snu, palenie, hałas, czystość, praca zdalna, alkohol i tagi stylu życia), pomaga przewidzieć, że A przesunie profil B w prawo, bardziej niż zgodność wieku i wspólne zainteresowania?

**Intuicja:** przy wspólnym mieszkaniu liczą się codzienne nawyki bardziej niż wspólne hobby czy podobny wiek.

**Jednostka analizy:** jeden skierowany swipe A→B na profil; wynik `y_right` (1 = prawy).

**Próba główna:** 92 754 swipe'y (1525 nadawców, 1354 odbiorców, 20,7% prawych). Lejek: 116 414 wszystkich swipe'ów → 95 144 na profile → 94 295 po wykluczeniu kont z Hyderabadu → 93 717 ze znanym wiekiem obu stron (próba H2/H3a) → 92 754 z co najmniej jednym wspólnie znanym polem stylu życia (próba H1).

## 2. W jaki sposób

- **Cechy z dnia swipe'a**, nie z bieżącego profilu (reguła as-of, D7); tagi stylu życia uzupełniają braki pól strukturalnych, a zainteresowania są oczyszczone z tagów stylu życia (D12, D13).
- **Trzy bloki zmiennych**, po 3 zmienne każdy:
  - wiek: ta sama grupa wiekowa, odległość grup, kierunek (odbiorca − nadawca);
  - zainteresowania: Jaccard, liczba wspólnych, różnica liczby tagów;
  - styl życia: odsetek zgodnych pól, konflikt kierunkowy tagów, liczba wspólnych tagów.
- **Identyczne kontrole we wszystkich modelach:** para płci nadawca→odbiorca (8 zmiennych, np. F→M, M→F) i miasto. Wcześniej model stylu życia ich nie miał.
- **Regresja logistyczna** z błędami klastrowanymi po nadawcy i odbiorcy (ta sama osoba występuje w wielu swipe'ach).
- **Kryterium z karty:** przyrost dopasowania po dodaniu stylu życia vs po dodaniu wieku i zainteresowań, z przedziałem ufności różnicy. Przyrosty liczone jako blok pierwszy, ostatni i średnio po wszystkich 6 kolejnościach.
- **Przedziały ufności:** bootstrap klastrowy (1000 powtórzeń, ziarno 42) osobno po nadawcach i po odbiorcach; jako konserwatywny przyjmujemy szerszy.
- **Walidacja poza próbą:** 5 foldów, każdy nadawca w jednym foldzie; logloss, AUC i AUC-PR; sparowane różnice modeli z bootstrapem po nadawcach.
- **Kontrole dodatkowe:** test tasowania stylu życia między odbiorcami; baseline losowych par dla zainteresowań; analiza każdego z 7 pól stylu życia (korekta Holma); 12 scenariuszy wrażliwości.

## 3. Dlaczego tak

- Zasady kursu: liczy się **wniosek o zakresie i pewności zgodnych z dowodami**, a nie wynik modelu; dobrze uzasadniony wynik negatywny jest pełnoprawny.
- Użytkownicy powtarzają się w wielu parach, więc błędy i przedziały muszą uwzględniać klastrowanie; foldy muszą być po użytkownikach, by nie było wycieku.
- Bloki mają różną liczbę zmiennych i są skorelowane, stąd obie kolejności dodawania, średnia po kolejnościach i ΔLL na stopień swobody.
- Identyczne kontrole są konieczne, by różnica między blokami nie wynikała z tego, że jeden blok „dostał” płeć, a inny nie.

## 4. Wyniki

### 4.1 Główne: kryterium H1

| Pytanie | Wynik | 95% CI |
|---|---|---|
| Średni przyrost ΔLL: wiek / styl życia / zainteresowania | 533,2 / 42,5 / 13,9 | (naiwne, bez klastrowania) |
| Styl życia − wiek+zainteresowania (ΔLL) | **−504,5** | [−883; −301] |
| Styl życia − wiek (ΔLL) | −487,8 | [−846; −273] |
| Styl życia − zainteresowania (ΔLL) | +27,0 | [−59; +106] (nierozstrzygnięte) |
| CV, styl życia − wiek+zainteresowania: logloss | −0,0053 | [−0,0087; −0,0021] |
| CV: AUC | −0,0224 | [−0,0330; −0,0117] |
| CV: AUC-PR | −0,0310 | [−0,0499; −0,0164] |

Wniosek jest taki sam dla każdej definicji przyrostu i w każdym z 12 scenariuszy wrażliwości (ΔLL stylu życia 29–66, ΔLL wieku+zainteresowań 354–890; to wartości naiwne, bez osobnych CI).

### 4.2 Wiek: kierunek, nie podobieństwo

Przy efektach stałych grupy wiekowej nadawcy, względem tej samej grupy wiekowej:

| Odbiorca | OR | 95% CI |
|---|---|---|
| młodszy o 1 grupę | 0,97 | [0,87; 1,09] |
| starszy o 1 grupę | 0,62 | [0,57; 0,68] |
| starszy o 2 lub więcej | 0,35 | [0,29; 0,43] |

To jest **kara za starszego odbiorcę**, a nie preferencja podobnego wieku. Po uwzględnieniu odległości i kierunku sama zgodność grupy nie jest istotna (OR 0,78 [0,56; 1,07]). Wcześniejszy wniosek („preferencja podobnego wieku”) był błędem interpretacyjnym i został wycofany.

### 4.3 Styl życia: słaby sygnał, bez zysku poza próbą

- Ponad przypadek: ΔLL 40,5 wobec 5,1 [0,4; 15,6] z tasowania odbiorców (p na minimum rozdzielczości testu).
- Poza próbą jako ostatni blok: AUC +0,0017 [−0,0008; 0,0040], logloss −0,0000 [−0,0007; 0,0006], AUC-PR −0,0021 [−0,0066; 0,0014]. Brak mierzalnej poprawy.
- Per pole: **żadne z 7 pól nie przechodzi korekty Holma** (najmniejsze p po Holmie 0,57). Naiwne ΔLL jest mylące: np. `work_from_home` ma ΔLL 54, a test Walda z klastrowaniem daje p = 0,26.
- Palenie (eksploracyjnie): niepalący → użytkownik OR 0,86 [0,78; 0,95], ale asymetrii kierunku nie wykazano (p = 0,65).
- Jedyny przypadek na korzyść stylu życia nad zainteresowaniami: AUC jako blok pierwszy (+0,0075 [0,0013; 0,0139]). Znika dla logloss, AUC-PR i bloku ostatniego, więc nie traktujemy tego jako wsparcia H1.

### 4.4 Zainteresowania

Prawe swipe'y mają nieco wyższy średni Jaccard (0,0694) niż losowe pary o tej samej liczbie tagów (0,0652 [0,0637; 0,0666]); lewe są na poziomie przypadku (0,0654 wobec 0,0658). Różnica prawe − lewe to 0,0040 [−0,0021; 0,0104] i **po uwzględnieniu klastrowania nie różni się od zera** (IDF-Jaccard: 0,0038 [−0,0014; 0,0090]). Zainteresowania dają najmniej ze wszystkich bloków.

## 5. Wnioski

1. **H1 nie została potwierdzona.** W danych z aplikacji styl życia przewiduje prawy swipe słabiej niż wiek; różnica jest duża i jej CI nie obejmuje zera.
2. **Prawy swipe przewiduje przede wszystkim to, kto kogo ogląda:** para płci i wiek odbiorcy względem nadawcy. Same kontrole dają w CV AUC 0,616, a dodanie wieku podnosi go do 0,642.
3. **Styl życia vs zainteresowania pozostaje nierozstrzygnięte** na tych danych.
4. **Brak mierzalnego efektu nie dowodzi, że styl życia nie ma znaczenia przy wyborze współlokatora.** Dowodzi tylko, że ten pomiar w tym etapie decyzji niewiele dodaje (patrz ograniczenia).

## 6. Ograniczenia

- **Rozdzielczość pomiaru.** Pięć z siedmiu pól stylu życia ma 74–81% braków na poziomie profili; na poziomie par braki u którejkolwiek strony to 47–92% swipe'ów. `cleanliness` i `noise_level` (ok. 2% braków) mogą być wartościami domyślnymi, co sztucznie zawyża ich „zgodność”. Wiek jest kompletny, ale gruby (4 grupy). Porównanie bloków zależy więc od jakości pomiaru, nie tylko od realnego związku.
- **Widoczność cech (hipoteza niezweryfikowana).** Możliwe, że wiek jest dla użytkowników bardziej widoczny niż pola stylu życia. Dane tego nie rozstrzygają (brak zdjęć, nieznana widoczność pól i tagów); to pytanie do dostawcy.
- **Ekspozycja i próba.** Widzimy tylko pary pokazane przez feed; 65% wyświetlanych profili to grupa 18–20; próba jest wąska (studencka).
- **Match i swipe to nie najem.** Wnioski dotyczą prawego swipe'a.
- **Specyfikacja poprawiona po obejrzeniu pierwszych wyników** (kontrola płci, specyfikacja wieku). Dlatego nawet analiza konfirmacyjna ma stopnie swobody badacza; raportujemy wszystkie warianty, a wniosek jest ten sam w każdym.
- **Techniczne:** ΔLL na poziomie swipe'a zakłada niezależność obserwacji i zawyża dowód (o kryterium rozstrzygają CI z bootstrapu klastrowego); CI w CV są warunkowe na dopasowanych modelach foldów; nie użyto modelu z efektami losowymi (jak w H3a); 963 swipe'y bez żadnego wspólnie znanego pola stylu życia wypadają z modelu.
- **Instrument AI:** normalizacja i klasyfikacja tagów przez agenta nie była walidowana względem człowieka (brak raportu κ); lista zadań jest w `docs/h1/open-questions.md`.

## 7. Co jest konfirmacyjne, a co eksploracyjne

| Analiza | Status |
|---|---|
| CI różnicy przyrostów (kryterium karty), CV po użytkownikach, test tasowania | konfirmacyjne (specyfikacja kontroli poprawiona po audycie) |
| Scenariusze D6, D7, G6; kwadrat różnicy wieku; IDF-Jaccard; baseline losowych par | pre-rejestrowana wrażliwość |
| Para płci zamiast `same_sex`, efekty stałe grupy nadawcy, kontrola sufitu 9 tagów | post hoc (audyt), raportowane |
| Rozkład na 3 bloki (Shapley), kierunek wieku, analiza per pole, kierunek palenia | eksploracyjne / post hoc |

## 8. Co zmienił audyt

Wniosek „H1 niepotwierdzona” się nie zmienił, ale zmieniło się jego uzasadnienie. Wcześniej: „dominują wiek i zainteresowania” (znak różnicy wieku czytany jako podobieństwo). Teraz: dominuje sam wiek (jako kierunek), zainteresowania są najsłabsze, a styl życia jest słabym sygnałem bez zysku poza próbą. Usunięto też nieweryfikowalne twierdzenie o zdjęciu profilowym i przewijaniu pól.
