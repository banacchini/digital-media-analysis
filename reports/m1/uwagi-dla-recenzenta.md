# Karta M1: uwagi dla recenzenta

Lista do review karty `reports/m1/karta-m1.typ` (przygotowanej przez agenta według `docs/prompts/m1-generation-plan.md`).

## Rozbieżności między artefaktami (rozstrzygnięte na korzyść notebooka)

| Wartość | Plik z hipotezami | Notebook `EDA` | W karcie |
|---|---|---|---|
| Pary bez kont skrajnych, n_min = 10 | 5533 | 5527 (sekcja „Liczność prób po filtrach aktywności”) | 5527 |
| Zmienna główna | H1: `y_match` główna, `y_right` wtórna | n/d | `y_right` główna (decyzja D4) |
| H2 | model dwuetapowy „bramki” i próg „bliskie zeru” | n/d | oszacowanie wielkości efektu (decyzja D17) |

- Notebook `EDA-rendered.ipynb`, o którym mówi plan, nie istnieje w repo. Liczby i rysunki wzięto z wyników zapisanych w `notebooks/EDA.ipynb`, bez uruchamiania kodu.

## Pozycje `[DO POTWIERDZENIA]` w karcie

- Skład zespołu (nagłówek).
- Właściciel danych, warunki użycia i data otrzymania (sekcja 2).
- H3b (podobieństwo treści bio): zakres zależny od zasobów (A4).
- Ujednolicenie i deduplikacja tagów (A3).
- Estymator (D18) oraz kontrole i efekty losowe (A2).
- Miara zgodności agenta AI z człowiekiem (D19).
- Podział zadań na M2 i M3 (sekcja 7).
- Review zespołu przed oddaniem (A5, sekcja 8).
- Długość karty (A1): obecnie 6 stron A4. Limit A1 (≤ 4 strony) przekroczony decyzją autora: schemat danych i tabele kolumn trafiły do treści karty, nie do załącznika.

## Pozycje `[DO PRZELICZENIA]`

- Liczności po filtrze Hyderabad (D10): użytkownicy, swipe'y, pary, matche.
- Udziały źródeł wersji profilu (54 597 / 61 118 / 551 / 148), liczone na 116 414 swipe'ach razem z ogłoszeniami: przeliczyć dla 95 144 swipe'ów na profile.

## Rysunki

Rysunki wyodrębniono z zapisanych wyników `EDA.ipynb` do `reports/m1/figures/`:

| Rys. | Plik | Komórka `EDA` (sekcja) |
|---|---|---|
| 1 | `R3_aktywnosc_selektywnosc.png` | „Aktywność użytkowników” |
| 2 | `R2_kompletnosc_pol.png` | „Pola stylu życia: kompletność i wartości domyślne” |
| 3 | `R1_akceptacja_plec.png` | „H2: przedziały ufności” |
| 4 | `R4_wiek_ekspozycja_akceptacja.png` | „Sprawdzenie ekspozycji oraz stopnia akceptacji” |

Żaden podpis nie ukrywa konfliktu z decyzjami, więc lista `[WYMAGA PRZEGENEROWANIA]` jest pusta. Warto jednak poprawić przy przegenerowaniu (kosmetyka):

- Rys. 4: literówka w tytule („Heeatmapa”), angielskie podpisy osi (`sender_age`, `target_age`), pasma 27+ niepołączone (D9; podpis o tym informuje).
- Rys. 1: literówka na osi X („spiwe'ów”).
- Rys. 2: obejmuje też pola spoza bloku stylu życia (`budget`, `room_type`, `move_in_month_offset`); podpis o tym informuje.
- Styl karty (tło, krój, nagłówki, tabele) jest według `STYLEGUIDE.md`, ale rysunki zostały w kolorach z notebooków (niebieski matplotlib, viridis), bo plan zabrania ich ponownego rysowania. Przy przegenerowaniu: seria główna `#A247E3`, porównanie `#234CE0`, baseline `#595959`, krój Plus Jakarta Sans (`STYLEGUIDE.md`, sekcja 8); mapa cieplna R4 może zostać sekwencyjna (styleguide nie definiuje skali ciągłej).
- Rysunki 1–4 są sprzed D7/D10 (bieżąca płeć z `users`, surowe tagi, z Hyderabad). Po przeliczeniu przez zespół (plan, sekcja 7) podmienić pliki pod tymi samymi nazwami.

## Schemat danych i tabele kolumn

- Rys. 1 (schemat tabel) jest narysowany w Typst na podstawie `data/tables_metadata.json`, bez danych. Liczba rysunków to 6, czyli powyżej limitu 3–4 z planu (sekcja 4), decyzją autora.
- Powiązania `chats` → `users` i `listings.owner_key` → `users` są oznaczone jako niesprawdzone (linia przerywana): w artefaktach nie ma kontroli spójności tych kluczy. Warto ją dodać w notebooku.
- Tab. 1–3: znaczenia kolumn z `users_overview` (sekcja 2) i `profile_history_overview` (sekcja 1), braki z `users_overview` (sekcja 3), pozostałe liczby z `EDA` i dokumentu technicznego. `hours_to_first_message` opisano jako jedyną miarę czasu poniżej dnia na podstawie nazwy kolumny i `reports/figures/04_temporal_granularity.png`; rozkład tej kolumny nie był sprawdzany.
- Rysunki `reports/figures/01`–`05` nie trafiły do karty: 02 i 03 opisują odrzucone hipotezy (dawne H3, H4), 01 ma stare ID i ucięte kolumny, 04 podaje `swipes.day` od 0 (dane: od 1).

## Rys. 2: styl życia w tagach i polach

- Rysunek jest złożony w Typst z liczb zapisanych w wynikach `EDA` (10 najczęstszych tagów, komórka „Analiza zainteresowań”) i `users_overview` (braki pól). To odstępstwo od reguły planu „tylko rysunki z notebooków”, na prośbę autora; nowych obliczeń nie było.
- Kolory to wstępny podział tagów: `student` = status (D12), zwierzęta i `extrovert`/`introvert` = styl życia (D12), `non_smoker` = styl życia (D15), `likes_calm` i `night_owl` = styl życia (dokument techniczny, sekcja 2.2 pkt 4). `cooking` i `movies_cinema` jako hobby to propozycja agenta; `values_privacy` nieprzypisany. Do zatwierdzenia przy zamrożeniu codebooka.
- Pary tag–pole (`non_smoker`/`smoker`/`vapes` ↔ `smoking` itd.) pochodzą z dokumentu technicznego (H1, plan pomiaru). Liczba użytkowników z pustym `smoking` (1637) jest z `users_overview`, sekcja 3. Liczności pozostałych tagów z par nie były liczone.
