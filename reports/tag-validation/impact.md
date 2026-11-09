# Walidacja tagów: wpływ decyzji na H1 (Z5)

Liczby pochodzą z `impact.json`. Specyfikacja jak w głównej analizie H1 (pooled logit, te same kontrole); ΔLL bloku = średnia po 6 kolejnościach wejścia bloków. Referencja: jeden recenzent, runda 1 (patrz `docs/tag-validation/decisions.md`). Kontrakt danych, mapowanie i propozycja bez zmian: tak.

## Pytanie: czy wniosek H1 zmienia się przy mapowaniu konsensusu?

**Kolejność bloków nie zmienia się** w scenariuszach (i)–(vi): w baseline wiek > styl życia > zainteresowania (ΔLL 533,2 / 42,5 / 13,9). Udział wieku w sumie ΔLL wynosi 89,3%–90,6% (baseline 90,4%).

Zmienia się **odstęp między stylem życia a zainteresowaniami**: stosunek ΔLL stylu życia do zainteresowań spada z 3,05 (baseline) do 1,71 w (ii) i 1,41 w (vi) (zakres w (i)–(vi): 1,41–3,05). ΔLL zainteresowań rośnie z 13,93 do 23,65 w (ii), a stylu życia spada z 42,51 do 40,37 w (ii) i 32,59 w (vi).

## Scenariusze

| Scenariusz | n próby | swipe'y ze zmianą zainteresowań | swipe'y ze zmianą pola stylu życia | ΔLL wiek | ΔLL zainteresowania | ΔLL styl życia | Jaccard zainteresowań, prawe | Jaccard zainteresowań, lewe | kolejność |
|---|---|---|---|---|---|---|---|---|---|
| (i) mapowanie agenta (baseline) | 92754 | 0,0% | 0,0% | 533,19 | 13,93 | 42,51 | 0,0698 | 0,0659 | wiek > styl życia > zainteresowania |
| (ii) konsensus A+B | 92754 | 56,6% | 0,0% | 533,42 | 23,65 | 40,37 | 0,0670 | 0,0623 | wiek > styl życia > zainteresowania |
| (iii) konsensus tylko A | 92754 | 4,1% | 0,0% | 533,21 | 13,97 | 42,45 | 0,0698 | 0,0659 | wiek > styl życia > zainteresowania |
| (iv) konsensus tylko B | 92754 | 54,5% | 0,0% | 533,41 | 23,55 | 40,51 | 0,0670 | 0,0623 | wiek > styl życia > zainteresowania |
| (v) agent, D13 wyłączone | 92247 | 0,0% | 74,9% | 523,91 | 14,46 | 43,16 | 0,0696 | 0,0658 | wiek > styl życia > zainteresowania |
| (vi) konsensus A+B + scalenia | 92754 | 56,6% | 0,0% | 533,77 | 23,09 | 32,59 | 0,0670 | 0,0623 | wiek > styl życia > zainteresowania |
| (diag) konsensus A+B, kod zastępczy `lifestyle` z often_out | 92754 | 56,6% | 25,6% | 533,94 | 23,81 | 37,87 | 0,0670 | 0,0623 | wiek > styl życia > zainteresowania |
| (diag) (vi) + kod zastępczy `lifestyle` z often_out | 92754 | 56,6% | 40,3% | 534,44 | 23,29 | 29,46 | 0,0670 | 0,0623 | wiek > styl życia > zainteresowania |

Zmiana liczona względem baseline na swipe'ach próby H1 (n = 92754); pole stylu życia: statusy zgodności siedmiu pól i kierunek palenia. Zmiana wartości pola bez zmiany statusu zgodności nie jest widoczna.

Zmiany względem baseline (Δ):

| Scenariusz | Δ ΔLL wiek | Δ ΔLL zainteresowania | Δ ΔLL styl życia | Δ Jaccard prawe | Δ Jaccard lewe |
|---|---|---|---|---|---|
| (ii) konsensus A+B | 0,23 | 9,72 | -2,14 | -0,0027 | -0,0036 |
| (iii) konsensus tylko A | 0,02 | 0,05 | -0,06 | 0,0000 | 0,0000 |
| (iv) konsensus tylko B | 0,22 | 9,62 | -2,00 | -0,0027 | -0,0036 |
| (v) agent, D13 wyłączone | -9,28 | 0,53 | 0,65 | -0,0002 | -0,0001 |
| (vi) konsensus A+B + scalenia | 0,58 | 9,16 | -9,92 | -0,0027 | -0,0036 |
| (diag) konsensus A+B, kod zastępczy `lifestyle` z often_out | 0,75 | 9,88 | -4,64 | -0,0027 | -0,0036 |
| (diag) (vi) + kod zastępczy `lifestyle` z often_out | 1,25 | 9,36 | -13,05 | -0,0027 | -0,0036 |

W (v) próba kurczy się do 92247 swipe'ów (−507), bo bez uzupełniania pól tagami 74,9% swipe'ów zmienia status zgodności któregoś pola.

## Scalenia (vi): D13 i D15

Klucze D13 przepięte na tag docelowy: 3 (quiet_evenings → likes_calm (noise_level=Q), silence_after_22 → likes_calm (noise_level=Q), peace_and_quite → likes_calm (noise_level=Q)). Kody tych kluczy są identyczne, więc przepięcie nie zmienia uzupełniania.

Pary polaryzacji (D15) dotknięte scaleniami: 3 wpisów.
- grupa 4, strona pos: `quiet_evenings` → `likes_calm` (usuwany tag jest w grupie; cel już w grupie: tak).
- grupa 4, strona pos: `peace_and_quite` → `likes_calm` (tag spoza grupy trafia do niej przez cel scalenia; cel już w grupie: tak).
- grupa 4, strona pos: `silence_after_22` → `likes_calm` (usuwany tag jest w grupie; cel już w grupie: tak).

Skutek (ii → vi) na próbie H1 (n = 92754): konflikt D15 przybywa w 0 swipe'ach i ubywa w 0 (odsetek konfliktów 52,4% → 52,4%). Liczba wspólnych tagów stylu życia rośnie w 9054 swipe'ach i maleje w 397 (średnia 1,004 → 1,099).

## going_out_friends → often_out: efekt słownika vs efekt uzupełniania pól

- **Przy obecnej mapie D13 efekt uzupełniania wynosi 0:** `TAG_TO_STRUCTURED_FIELD_MAP` nie zawiera `often_out` ani `going_out_friends`, a kody pola `lifestyle` (S/M/W) nie mają znaczenia w codebooku. Status zgodności pola `lifestyle` zmienia się w 0,0% swipe'ów między (ii) a (vi). Pole „brak → lifestyle” w propozycji (`proposed_linked_field`) nie jest używane w budowie zbioru H1.
- **Efekt słownika (vi − ii):** ΔLL wiek 0,35, zainteresowania -0,56, styl życia -7,78.
- **Diagnostyka z kodem zastępczym** (`OUT` uzupełnia `lifestyle` z `often_out`, przed scaleniem także z `often_outside`; to założenie, nie dane): status pola `lifestyle` zmienia się w 25,6% swipe'ów bez scalenia, w 40,3% ze scaleniem; 17,5% swipe'ów zmienia status wyłącznie przez to, że `going_out_friends` zaczyna uzupełniać pole.
- Efekt uzupełniania na ΔLL stylu życia: -2,50 bez scalenia, -3,13 ze scaleniem; różnicę wynikającą ze scalenia daje -0,63 (wiek 0,15, zainteresowania 0,04).

## Zastrzeżenia

- Referencja to jeden recenzent bez testu powtórnego; zmiany kategorii B przesunęły część tagów (5 różnic względem Claude) i 8 mapowań surowych (A).
- Nie ma przedziałów ufności dla różnic między scenariuszami; to są różnice punktowe na tej samej próbie, nie testy.
- Tekst H1 nie został zmieniony; decyzja o v1 należy do zespołu.
