# M1 RentFriends: decyzje zespołu i instrukcja dla agenta

Zadanie: przygotuj **kartę eksploracji danych (M1)** na podstawie decyzji z sekcji 2, założeń z sekcji 3, planu rysunków z sekcji 4 i artefaktów z sekcji 6. Wynik oceni człowiek (review obowiązkowe).

## 0. Reguły dla agenta

1. **Liczby tylko z artefaktów** (notebooki, plik z hipotezami). Nie szacuj ani nie przeliczaj z pamięci. Czego nie ma w artefaktach, oznacz `[DO POTWIERDZENIA]`.
2. **Nie czytaj `data/processed` i nie uruchamiaj notebooków** (zgodnie z `AGENTS.md`). Nie wyświetlaj treści `bio`. Pracuj na artefaktach zagregowanych i na wynikach zapisanych w notebookach.
3. **Rozbieżności** między plikiem z hipotezami a notebookiem rozstrzygaj na korzyść notebooka i wypisz je w osobnej liście dla recenzenta (np. 5533 vs 5527 par bez kont skrajnych dla n_min = 10).
4. **Liczby w notebookach są sprzed decyzji D7 i D10** (wersjonowanie cech, filtr Hyderabad). Oznaczaj je w karcie jako „przed odfiltrowaniem Hyderabad (45 kont)”. Udziały swipe'ów z audytu `profile_history` (54 597 = 46,9%; 61 118 = 52,5%; 551; 148) liczono na **wszystkich 116 414 swipe'ach, razem z ogłoszeniami**, więc podaj je z tą adnotacją i `[DO PRZELICZENIA dla 95 144 swipe'ów na profile]`.
5. **Numeracja hipotez:** w artefaktach obowiązują stare ID (H1, H2, H5). W karcie używaj **nowych** (D2) i przy pierwszym użyciu podaj odpowiednik z dokumentu technicznego.
6. Język: polski. Bez języka przyczynowego („wpływa”, „determinuje”): używaj „jest związane z”, „przewiduje”.
7. Karta ma być **jak najbardziej zwięzła, ale dokładna** i odpowiadać na każdy element z opisu M1 (sekcja 1). Szczegóły odsyłaj do dokumentu technicznego.

## 1. Struktura karty (1:1 z opisem M1 w zasadach kursu)

M1 oceniane jest za: konkretność pytania, jakość eksploracji, spójność planu badawczego. Sekcje:

1. **Pytanie badawcze i hipotezy**
2. **Źródła danych**
3. **Zakres próby**
4. **Wyniki wstępnej eksploracji** (opisowe, bez wnioskowania statystycznego; tu trafiają rysunki z sekcji 4)
5. **Plan pomiaru zjawiska**
6. **Ograniczenia danych i możliwe źródła błędu**
7. **Wykonalność w skali kursu** (w tym scenariusze zależne od otwartych kwestii)
8. **Dane osobowe i ujawnienie użycia AI** (krótko)

## 2. Decyzje zespołu (potwierdzone)

**Pytanie i hipotezy**
- D1. Pytanie zawężone: nie obserwujemy najmu, badamy **prawy swipe i match** w aplikacji. Karta mówi to wprost.
- D2. Zostają trzy hipotezy, **przenumerowane**:

  | Nowe ID | Treść | Dawne ID (dokument techniczny, notebooki) |
  |---|---|---|
  | H1 | styl życia przewiduje match silniej niż wiek i zainteresowania | H1 |
  | H2 | dopasowanie demograficzne (płeć, wiek): oszacowanie wielkości efektu | H2 |
  | H3 | treść i staranność bio (hipoteza dodatkowa) | H5 |

  Dwie hipotezy wymagające kolejności zdarzeń w obrębie dnia (dopasowanie dwustronne, zgodność selektywności użytkowników) są **odrzucone**: dane mają tylko `day`, a po filtrach zostaje 87 matchy. Opisz to w jednym przypisie, bez nadawania im ID (żeby nie kolidowały z nowym H3).
- D3. **H3 (dawne H5) jest hipotezą dodatkową**: zakres części NLP jest niepewny.

**Zmienne, jednostka analizy, próba**
- D4. Zmienna główna: **`y_right`** (swipe kierunkowy A→B na profil). Match: drugorzędna. Rozmowy: tylko opisowo (2310 z 2742 powstaje poza matchem i ogłoszeniem).
- D5. Modele matcha: **tylko pary z zapisanymi oboma swipe'ami** (487 matchy z 7790 par). 246 matchy z jednym swipe'em poza modelem.
- D6. Analiza główna **bez progu aktywności i bez wykluczania kont skrajnych**. Próg (≥ 10 swipe'ów) i wykluczenie kont skrajnych (18 z samymi prawymi, 359 z samymi lewymi) to **analiza wrażliwości**.
- D7. **Reguła wersji profilu (as-of):**
  1. swipe z dnia późniejszego niż dzień pierwszej wersji → **ostatnia wersja sprzed dnia swipe'a**;
  2. swipe z dnia pierwszej wersji (i analogicznie sprzed niej) → **pierwotna, najstarsza wersja (v1)**;
  3. użytkownicy bez historii (9 w `users`) → **bieżący `users`**.
  Każdy swipe dostaje flagę źródła: `prior_version` / `first_version` / `users_current`. Wersja z `users` jako wrażliwość oraz wrażliwość tylko na swipe'ach z `prior_version`.
- D8. Płeć **`O` jako osobna kategoria** (65 ze 101 zmian płci prowadzi do `O`: wnioski o `O` ostrożne).
- D9. Wiek: różnica numerów `age_band` (ze znakiem) i wskaźnik tego samego pasma; pasma **27+ połączone**.
- D10. **Odfiltrowujemy konta z miastem Hyderabad** (45 użytkowników; anomalia dla polskiej aplikacji) z analizy głównej, wraz ze swipe'ami, w których są nadawcą lub odbiorcą. Kategoria „inne” **zostaje**. Wrażliwość: wersja z Hyderabad.

**Styl życia i zainteresowania (H1)**
- D11. Ujednolicenie tagów (54 formy emoji → kanoniczne) wykonuje **agent AI, z review człowieka**.
- D12. Klasyfikacja tagów: **`student` = status** (poza blokiem stylu życia); **zwierzęta = styl życia**; **`extrovert`/`introvert` = styl życia**; hobby = blok zainteresowań.
- D13. Gdy tag i pole strukturalne opisują to samo: **pole strukturalne ma pierwszeństwo, tag uzupełnia braki, zgodność raportowana**.
- D14. Blok stylu życia zawiera **siedem pól strukturalnych** (`daily_routine`, `lifestyle`, `work_from_home`, `cleanliness`, `noise_level`, `smoking`, `alcohol`) oraz tagi stylu życia (np. `quiet_after_22`). Braki (74–81% w większości pól): kategoria „brak danych”; konflikt liczony tylko tam, gdzie znane są obie strony. Kody pól nie mają codebooka, więc dla nich tylko zgodność równości, bez kierunku.
- D15. Dopasowanie stylu życia: **wskaźniki konfliktu kierunkowego (dla par tagów o jasnym kierunku, np. `non_smoker` vs `smoker`/`vapes`) + liczba wspólnych tagów** (nie sam Jaccard).

**Metodologia**
- D16. Porównanie bloków: **bootstrap po użytkownikach**, **obie kolejności** dodawania bloków, **1–3 skalary na blok**. Analiza per pole jest drugorzędna.
- D17. **H2 przeformułowana jako oszacowanie wielkości efektu** (np. iloraz szans: ta sama vs różna płeć, według płci nadawcy, z CI). Bez progu „bliskie zeru” i bez modelu dwuetapowego „bramki”. Zaznacz, że macierz P(prawy) była widziana przed formalizacją hipotezy (część eksploracyjna).
- D18. Walidacja: **foldy po użytkownikach**. Estymator `[DO POTWIERDZENIA]` (kandydaci: model z crossed random effects nadawcy i odbiorcy; regresja logistyczna z błędami klastrowanymi).

**Instrument AI i prywatność**
- D19. **Instrument AI:** klasyfikacja tagów przez agenta AI z recenzją człowieka. Walidacja = zgodność propozycji agenta z finalnym podziałem człowieka; propozycje agenta zapisz **przed** zamrożeniem codebooka. Dla H3 (jeśli będzie NLP): gold standard z ręcznie oznaczonej próbki, lokalnie. Szczegóły (rozmiar próbki, adnotatorzy) opisz jako nieustalone.
- D20. `bio` przetwarzane dotąd tylko zagregowanie (opis w `AGENTS.md`); ewentualne NLP **tylko lokalnie**.

**Format i dostawca**
- D21. **Pytań do dostawcy nie da się zadać przed kartą.** Otwarte kwestie opisz w karcie jako ryzyka z scenariuszami „jeśli A, to wykonalność/interpretacja X”.
- D22. W karcie **wykorzystujemy grafiki z analiz**, gdzie to stosowne, według zasad z sekcji 4.

## 3. Założenia domyślne do potwierdzenia (agent stosuje, ale oznacza `[DO POTWIERDZENIA]`)

- **A1. Długość:** do 3 stron tekstu plus rysunki, łącznie nie więcej niż 4 strony.
- **A2. Kontrole:** `same_city`; efekty losowe nadawcy i odbiorcy (popularność i hojność).
- **A3. Duplikaty tagów w obrębie użytkownika po mapowaniu** (256 użytkowników ma oba formaty, 159 z nich na limicie 9): deduplikacja; podaj efektywną liczbę tagów.
- **A4. Zakres H3:** H3a (staranność bio: pusty/niepusty, długość) w zakresie karty; H3b (podobieństwo treści, ekstrakcja) tylko jako opcja zależna od zasobów.
- **A5. Sekcja o ujawnieniu użycia AI:** karta przygotowana z agentem Claude Code, prompt i logi w repo, review człowieka.
- **A6. Zestaw analiz wrażliwości (nazwij je w sekcji 5):** próg aktywności i konta skrajne (D6), tylko `prior_version` i wersja z `users` (D7), wersja z Hyderabad (D10), bez kategorii „brak danych” (D14).

## 4. Grafiki z analiz w karcie

Zasady:
1. **Tylko rysunki wygenerowane w notebookach** (bez nowych analiz). Agent **nie rysuje ich ponownie i nie uruchamia kodu**: wyodrębnia obrazy z zapisanych wyników notebooków (najlepiej z wersji `*-rendered`), a gdy to niemożliwe, zostawia placeholder z opisem.
2. **Limit: 3–4 rysunki** w całej karcie, w sekcji 4 (ewentualnie jeden w sekcji 3). Resztę wykresów zastąp tabelą albo odsyłaczem „pełny wykres: notebook X, sekcja Y”.
3. **Podpis każdego rysunku** („Rys. N.”, po polsku): co przedstawia, liczność, **podstawa danych**, zastrzeżenie. Dla rysunków sprzed decyzji dopisz: „wstępne: bieżąca płeć z `users`, surowe tagi, z Hyderabad”. Przedziały Wilsona oznacz jako „niezgrupowane po użytkowniku, zaniżone”.
4. Jeśli podpis musiałby ukrywać konflikt z decyzjami z sekcji 2, **nie używaj rysunku**, tylko wpisz go na listę `[WYMAGA PRZEGENEROWANIA]`.
5. **Prywatność:** żadnych rysunków ani tabel z danymi pojedynczych użytkowników (przykładowe profile z notebooków `users_overview` i `profile_history_overview`) ani z treścią `bio`.
6. Każdy rysunek: czytelne osie i legenda, niepewność widoczna tam, gdzie jest istotna, numeracja i odwołanie w tekście. Rysunki z angielskimi tytułami (`users_overview`, `profile_history_overview`) preferuj tylko, jeśli zespół je spolszczy.

Proponowany wybór (priorytet malejący):

| # | Rysunek | Źródło | Sekcja | Zastrzeżenie do podpisu |
|---|---|---|---|---|
| R1 | Akceptacja wg płci nadawcy i odbiorcy z CI Wilsona (F→M 8,7% vs F→F 20,1%) | `EDA`, sekcja „H2: przedziały ufności” | 4 (H2) | bieżąca płeć; CI zaniżone; `O` ostrożnie |
| R2 | Kompletność pól stylu życia (braki 74–81%; `cleanliness`/`noise_level` ok. 1%) | `EDA`, sekcja „Pola stylu życia” | 4 (H1) | możliwe wartości domyślne |
| R3 | Rozkład aktywności i selektywności użytkowników | `EDA`, sekcja „Aktywność użytkowników” | 4 | uzasadnia efekty losowe i konta skrajne; z Hyderabad |
| R4 | Macierz ekspozycji i akceptacji wg grup wiekowych | `EDA`, sekcja „ekspozycji oraz stopnia akceptacji” | 4 (H2) | małe komórki 27+; z Hyderabad |
| opc. | Liczba tagów na użytkownika (sufit 9) oraz najpopularniejsze tagi | `users_overview` (tagi) | 4 (H1) | surowe tagi z duplikatami formatów |
| opc. | Długość bio (znaki), sufit 250 | `EDA` (sekcja bio) | 4 (H3) | tylko długość |

Lejek (swipe → prawy → match → rozmowa), liczba rozmów poza matchem, pokrycie matchów swipe'ami i wersjonowanie profili podaj **tabelą lub liczbą w tekście**, nie rysunkiem.

## 5. Otwarte kwestie dla sekcji 6–7 (opisz scenariusze)

| Kwestia | Dotyczy | Co opisać w karcie |
|---|---|---|
| Działanie feedu (filtry, ranking, widoczność lajka) | H1, H2 | wpływ na ekspozycję (G1); efekty jako związki w obserwowanej ekspozycji |
| Widoczność tagów i bio na karcie | H1, H3 | brak efektu ≠ brak wpływu, jeśli cechy niewidoczne |
| 246 matchy z jednym swipe'em; superlajki (2310 rozmów poza matchem) | wynik drugorzędny | analiza wrażliwości; ograniczony wniosek o matchu |
| Kody pól stylu życia bez codebooka; możliwa wartość domyślna `cleanliness`/`noise_level` | H1 | tylko zgodność równości; wrażliwość bez tych pól |
| Znaczenie `O`, zmiany płci | H2 | ostrożna interpretacja `O` |
| Dzień zerowy; swipe'y z dnia pierwszej wersji i sprzed niej | as-of (D7) | flaga źródła wersji i wrażliwość |

## 6. Artefakty źródłowe (dostosuj ścieżki do repo)

- `docs/rentfriends_hipotezy_karta_eksploracji.md` (najnowsza wersja z dziennikiem audytu, sekcja 7; stare ID hipotez)
- `notebooks/EDA.ipynb` (wersja z wynikami: `EDA-rendered.ipynb`)
- `notebooks/users_overview.ipynb`, `notebooks/profile_history_overview.ipynb`
- `AGENTS.md`, `docs/RENTFRIENDS.md`, `data/tables_metadata.json`
- Zasady kursu (opis M1 i kryteria): sekcje 4.2 i 4.3

## 7. Zadania zespołu (poza agentem, najlepiej przed review)

- Przeliczyć udziały źródeł wersji (D7: `prior_version` / `first_version` / `users_current`) dla **95 144 swipe'ów na profile**.
- Policzyć liczności po filtrze Hyderabad (D10): użytkownicy, swipe'y, pary, matche.
- Powtórzyć Jaccard po ujednoliceniu tagów oraz macierz płci na płci z wersji as-of. Jeśli się nie uda przed M1, rysunki zostają jako „wstępne”.
- Wyeksportować rysunki R1–R4 (PNG lub SVG) z notebooków i podać ścieżki agentowi.

## 8. Lista kontrolna przed oddaniem do review

- [ ] Każdy element z sekcji 1 ma swoją sekcję karty.
- [ ] Każda liczba ma źródło w artefakcie; reszta oznaczona.
- [ ] Nowe ID hipotez (H1, H2, H3) użyte konsekwentnie, z odpowiednikiem przy pierwszym użyciu.
- [ ] Rysunki: ≤ 4, podpisane po polsku, z podstawą danych i zastrzeżeniem; brak danych indywidualnych.
- [ ] Liczby sprzed filtra Hyderabad i sprzed wersjonowania oznaczone jako takie.
- [ ] Wnioski bez języka przyczynowego; match ≠ najem wyrażone wprost.
- [ ] Wypisane rozbieżności i pozycje `[DO POTWIERDZENIA]`.
- [ ] Brak treści `bio` w jakiejkolwiek formie.
