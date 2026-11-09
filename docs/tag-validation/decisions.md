# Walidacja tagów: decyzja (jeden recenzent, jedna runda)

Data: 2026-11-09. Referencja: runda 1 Dominika (nie w pełni ślepa; bez testu powtórnego). Hash propozycji: `1e5625c5…2f94ab8`. Hash rundy 1 B: `2ab9d430…ed4cf`; hash rundy 1 A: `8dfc4307...375fd`.
Definicje kategorii użyte w arkuszu B: `codebook B-2`.

## 1. Werdykty reguły z prereg (metryki zamrożone, `summary.json` w commicie `[hash]`)

| Zadanie | Wynik | Reguła | Werdykt |
|---|---|---|---|
| A (raw → kanoniczny, n = 128) | zgodność 96,1% (123/128), κ 0,960 [0,928; 0,984], zgodność ważona swipe'ami 99,97% | ważona ≥ 95% | **mapowanie agenta zostaje** (+ 4 dopiski, patrz niżej) |
| B (kategorie, n = 68), Claude | zgodność 86,8% (59/68), κ 0,756 [0,632; 0,868], AC1 0,839, ważona 92,3% | κ ≥ 0,70 **i** ważona ≥ 95% | **niespełniona → kategorie z decyzji końcowej** |
| B, Gemini (informacyjnie) | zgodność 79,4%, κ 0,627 [0,479; 0,760], ważona 83,2% | j.w. | niespełniona |

Dodatkowo (nie zmienia werdyktu): A na 65 nietrywialnych pozycjach (emoji, formy polskie) 60/65 = 92,3%; wśród nich 4 pozycje bez wpisu w mapowaniu (tylko `profile_history`). B: bez `cooking` (42% wagi niezgodności) zgodność ważona byłaby 95,6%; przy traktowaniu `unclear` agenta jako wstrzymania się 95,1% (59/63). Referencja nie użyła `unclear` ani razu (hobby 37, lifestyle 30, status 1).

## 2. Zadanie A: decyzje

Niezgodności agent–referencja: 5. Decyzje końcowe i uzasadnienia:

| raw_tag | agent | referencja/decyzja | uzasadnienie |
|---|---|---|---|
| 🏃 Aktywność & sport | brak | active_sport | mapowanie 1:1 do active_sport |
| 💻 Pracuję zdalnie | brak | works_remote | mapowanie 1:1 do works_remote |
| 🤫 Spokojne wieczory | brak | quiet_evenings | semantycznie zgodne z quiet_evenings |
| 🧵 DIY / rękodzieło | brak | diy | mapowanie 1:1 |
| 🧘 Lubię spokój | peace_and_quite | likes_calm | mapowanie 1:1, po scaleniu tagów calmness/peace zgodność |

## 3. Zadanie B: decyzje końcowe względem rundy 1

Zmiany po przeglądzie (kolumna `konsensus`):

| tag | runda 1 | decyzja | uzasadnienie (z codebooka) |
|---|---|---|---|
| city_breaks | lifestyle | unclear | hobby, ale powoduje że osoba może mniej być w mieszkaniu (lifestyle) |
| healthy_food | hobby | unclear | hobby, ale może być traktowane jako wymóg współlokatora |
| marketing_social | hobby | unclear | niejasne |
| tech_it | hobby | unclear | niejasne |

Niezgodności z Claude, które **zostawiłem** (decyzja ≠ agent):

| tag | agent | decyzja | uzasadnienie |
|---|---|---|---|
| cooking | hobby | lifestyle | wpływa na użycie części wspólnych domu |
| instruments | hobby | lifestyle | wpływa na hałas w domu |
| vanlife | hobby | lifestyle | całkowita zmiana stylu życia |
| long_talks | unclear | lifestyle | wpływa na dynamike w domu |
| bussiness | unclear | hobby | spójność z tech_it i marketing_social |

Kryterium jednolite dla granicy hobby/lifestyle: `lifestyle to rzeczy które wpływają na dynamikę, sposób korzystania, lub obecność w mieszkaniu`. Uwaga: 3 z 4 zmian w tabeli powyżej przesuwają etykietę w stronę propozycji agenta po jej obejrzeniu; metryki w sekcji 1 pochodzą z rundy 1 i się nie zmieniają.

## 4. Scalenia (`tag_merge_map.csv`)

| źródło | cel | swipe'y (źródło) | uzasadnienie |
|---|---|---|---|
| quiet_evenings | likes_calm | 6 355 | ten sam konstrukt (spokój w mieszkaniu) |
| peace_and_quite | likes_calm | 398 | j.w.; literówka sluga |
| silence_after_22 | likes_calm | 18 038 | zbyt szczegółowe, wystarczy cisza w mieszkaniu |
| going_out_friends | often_out | 37 875 | wychodzenie poza dom; **zmienia też pole D13 (brak → lifestyle)**, skutek raportowany osobno |
| often_outside | often_out | 0 | duplikat; bez użycia w danych, scalenie nic nie zmienia |

## 5. Ograniczenia (do raportu)

Referencja: jeden recenzent, nie w pełni ślepy względem propozycji agentów (część pozycji wymieniono wprost w rozmowie), rzetelność oceny nieoszacowana (brak testu powtórnego). Wynik dotyczy zgodności agenta z zamierzeniem codebooka, nie poprawności kategorii. Dla tagów objętych D12 (`student`, zwierzęta, `extrovert`, `introvert`) zgodność wynika ze wspólnej reguły. Zgodność ważona dla B zależy od jednego tagu (`cooking`).

## 6. Co dalej

Zadanie C zamknięte (patrz tabela scaleń). Analiza wpływu (Z5): `[link do reports/tag-validation/impact.md]`. Decyzja o v1: `[uzupełnij po Z5]`.
