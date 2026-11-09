# Prompt: strumień grafowy (a: struktura, b: wzajemność, c: hierarchia pożądania)

## Rola i kontekst

Pracujesz w repo projektu RentFriends (kurs AMC, PWr). Dodajesz **nową, niezależną analizę sieciową** w pakiecie `src/rentfriends/graph/` (nowy), notebookach `notebooks/graph_*.ipynb`, dokumentach `docs/graph/` i wynikach `reports/graph/`. **Nie modyfikuj** `rentfriends.h1`, `rentfriends.h2`, `rentfriends.h3a` ani niczego poza wymienionymi ścieżkami; nie importuj z nich kodu. Inni agenci równolegle poprawiają te moduły i budują H3b, więc jedynym wspólnym wejściem jest **kontrakt danych v1**: zamrożony `data/processed/h1_analysis_dataset.parquet` (tylko do odczytu; zapisz jego sumę SHA-256 w `docs/graph/data-contract.md`) oraz surowe `swipes.parquet`, `users.parquet` (do odczytu).

Przeczytaj najpierw: `docs/prompts/m1-generation-plan.md` (decyzje D6–D18), `docs/codebook.md`, `rentfriends_hipotezy_karta_eksploracji.md` (G1–G18; szczególnie G1 ekspozycja/feed, G3 tylko `day`, G15 matche z jednym swipe'em), `STYLEGUIDE.md`, `data/README.md`.

### Pytania badawcze

- **(a) Informacja ze struktury.** Czy struktura grafu swipe'ów niesie informację o `y_right` ponad cechy pary i ponad same propensje węzłów (hojność nadawcy, popularność odbiorcy)?
- **(b) Wzajemność ponad propensje.** Czy liczba matchy w parach z decyzją obu stron przewyższa liczbę oczekiwaną przy niezależności (Σ p̂_AB·p̂_BA)?
- **(c) Hierarchia pożądania** (wg Bruch i Newman 2018, Science Advances: pożądanie jako wynik rankingu typu PageRank; szansa odpowiedzi maleje z różnicą pożądania). Czy na swipe'ach widać „ligi" i jak zmienia się wzajemność z różnicą pozycji?

Sukcesem **nie** jest wynik modelu. Wynik negatywny (brak informacji ze struktury ponad M1) jest pełnoprawnym wnioskiem. Wnioski dotyczą związku, nie przyczynowości; prawy swipe/match ≠ najem.

## Zasady nadrzędne

1. **Pre-rejestracja przed pierwszym uruchomieniem modeli.** Najpierw napisz i zacommituj `docs/graph/prereg.md` z: pytaniami, definicjami, splitami, drabiną modeli, kryteriami, siatką hiperparametrów, ziarnami. Zmiany po zobaczeniu wyników tylko jako osobny wpis `post hoc` z datą i powodem. **Nagłówkowym protokołem jest P1; P2 raportujesz zawsze w tej samej tabeli.** Nie wybieraj protokołu ani modelu pod „ciekawszy" wynik.
2. **Brak wycieku.** W zbiorze `h1_analysis_dataset.parquet` są kolumny policzone ze wszystkich swipe'ów: `sender_right_rate`, `sender_total_swipes`, `is_extreme_user`, `is_low_activity`, `match`. **Nie używaj ich jako cech.** Jeśli potrzebujesz statystyk z etykiet (stopień, odsetek prawych), licz je wyłącznie z krawędzi treningowych w danym foldzie.
3. **Dwa niezależne zbiory węzłów:** nadawcy i odbiorcy (ten sam użytkownik ma dwa węzły). Krawędź zwrotna B→A nie może trafić do cech ani grafu treningowego dla A→B w analizach (b) i (c) (patrz „Foldy dla (b) i (c)").
4. **Próba:** swipe'y na profile (bez swipe'ów na siebie), bez Hyderabadu (D10), complete-case jak w H2/H3a. Zrekonstruuj lejek 95 144 → 94 295 → 93 717 i zapisz, gdzie Twoja próba się różni i dlaczego. Konta skrajne zostają (D6); wrażliwość: bez nich.
5. **Prywatność:** brak `bio`. Żadnych `user_key` w wynikach i wykresach. Agregaty, komórki < 5 użytkowników tłumione. Żadnych zewnętrznych API.
6. **Stos:** czysty PyTorch na CPU (graf ma ok. 95 tys. krawędzi i ok. 3 tys. węzłów). PyG dopuszczalny tylko jeśli GraphSAGE z cechami okaże się potrzebny i da się go zainstalować bez walki ze środowiskiem. Wszystko deterministyczne (stałe ziarna).
7. Gałąź `feat/graph`, małe opisowe commity (jeden krok = jeden commit), bez squashowania. Testy i lintery przed commitem.
8. Niejednoznaczne decyzje: zapisz w `docs/graph/open-questions.md`, wybierz opcję konserwatywną z adnotacją.

## Definicje (zapisz w prereg.md)

**Cechy pary (stałe, z zamrożonego parquetu):** `sex_pair`, `same_band`, `age_band_diff`, `age_band_diff_abs`, `city_same`, `city_diff`, `interests_jaccard`, `interests_shared_n`, `lifestyle_agree_ratio`, `lifestyle_tag_conflict`, `lifestyle_shared_tags_n`. Braki: 0 + wskaźnik braku. Standaryzacja z danych treningowych.

**Drabina modeli** (wszystkie przewidują `y_right`, strata BCE):
- **M0**: regresja logistyczna na cechach pary.
- **M1**: M0 + efekty nadawcy i odbiorcy (one-hot ID z regularyzacją L2, ekwiwalent efektów losowych). To jest **baseline dla pytania (a)**.
- **M2**: M1 + faktoryzacja macierzy z cechami: `logit = b + a_s + c_r + u_s·v_r + w·x`, wymiar d.
- **M3**: LightGCN dwustronny (nadawcy ↔ odbiorcy), propagacja po krawędziach treningowych: osobne relacje dla prawych i lewych swipe'ów (jak w R-GCN uproszczonym); głowica jak w M2.
- **M4**: GNN z cechami węzłów (płeć, pasmo wieku, miasto, multi-hot zainteresowań, pola stylu życia), indukcyjny, agregacja sąsiedztwa; działa także dla nowych nadawców.

**Główny kontrast (a):** najlepszy z M2–M4 vs **M1**. Kryterium (do potwierdzenia przez zespół, domyślnie): struktura „wnosi", jeśli ΔlogLoss ≤ −0,002 i CI 95% nie obejmuje 0. CI poza marginesem, ale |Δ| < 0,002 = „wykrywalne statystycznie, praktycznie pomijalne". Wybór „najlepszego z M2–M4" robisz **wewnątrz foldów treningowych** (nie na testowych).

**Hiperparametry:** stała siatka ≤ 12 konfiguracji: d ∈ {8, 16, 32} × L2 ∈ {1e-4, 1e-3} × warstwy ∈ {1, 2}; AdamW, full-batch, maks. 300 epok, wczesne zatrzymanie (cierpliwość 20) na walidacji wewnętrznej (10% krawędzi treningowych, losowanych w obrębie nadawców). 5 ziaren; raportuj średnią i rozrzut.

**P1 (nagłówkowy, transduktywny):** 5-krotna walidacja po krawędziach, stratyfikowana po nadawcach (krawędzie każdego nadawcy losowo przypisane do 5 foldów). Ewaluacja na krawędziach testowych, gdzie nadawca i odbiorca mają ≥ 5 krawędzi treningowych; raportuj odsetek odrzuconych. **P2 (zimny start):** `GroupKFold` po nadawcach (5 foldów); w M1 brak efektu nadawcy (tylko odbiorcy), M3 nie dotyczy, M4 tak. Porównywalny z H1/H2 (AUC 0,58–0,63).

**Foldy dla (b) i (c):** foldy po **nieuporządkowanej parze {A,B}**: obie krawędzie pary zawsze w tym samym foldzie, więc predykcje p̂_AB i p̂_BA są cross-fitted i nie widziały etykiety zwrotnej. Uniwersum par: 7790 par z decyzją obu stron (487 matchy).

**Niepewność:** bootstrap po nadawcach na predykcjach out-of-fold (sparowane różnice strat); drugi widok: bootstrap po odbiorcach; podaj szerszy CI jako konserwatywny. Dla (b) i (c) „node bootstrap" (losowanie użytkowników, zachowanie par indukowanych).

## Zadania (w tej kolejności)

**Z0.** Kontrakt danych (SHA-256), szkielet pakietu, prereg.md (commit przed Z3).
**Z1.** Dane i grafy: budowa tabel krawędzi, lejek próby, testy: (i) żadna krawędź testowa nie występuje w macierzach sąsiedztwa, (ii) test permutacji etykiet testowych daje ≈ losowy wynik, (iii) kolumny wyciekowe nieobecne.
**Z2.** Splity P1, P2 i foldy par; testy własności (≥ 5 krawędzi, rozłączność par).
**Z3.** M0 i M1; odtwórz rzędy wielkości znane z H1/H2 (logloss ok. 0,50–0,52; AUC cech pary ok. 0,58–0,63 w P2). Duże odchylenia wyjaśnij.
**Z4.** M2–M4, siatka, ziarna.
**Z5.** **Symulacja mocy:** wygeneruj etykiety na rzeczywistej strukturze grafu (stopnie, ekspozycje) z M1 jako prawdą plus latentny czynnik o rosnącej sile; sprawdź, od jakiej siły pipeline wykrywa strukturę (kryterium Z-głównego). Wynik to „MDE struktury". Dla siły zero ΔlogLoss ma wyjść ≈ 0 (kontrola fałszywych alarmów).
**Z6.** Wyniki (a): tabele i metryki „plakatowe" (niżej), P1 i P2 obok siebie.
**Z7.** (b): obserwowane vs oczekiwane matche, kalibracja p̂ na uniwersum, rozkład wg koszyków oczekiwanej szansy, bootstrap. Główna analiza bez 246 par z jednym zapisanym swipe'em (G15); wrażliwość: te pary dopisane jako matche. Sprawdź kalibrację „w całości" na krawędziach uniwersum (jeśli p̂ jest tu skrzywione, oczekiwana liczba jest skrzywiona; opisz).
**Z8.** (c): pożądanie D(u) = efekt odbiorcy (cross-fitted, z foldów bez danej pary) w percentylach; wrażliwość: PageRank na krawędziach prawych z foldów treningowych. Krzywe: P(prawy swipe | różnica pożądania) oraz P(B→A prawo | A→B prawo, różnica) dla par z decyzją obu stron, kosze ≥ 100 par, CI z node bootstrap, obok krzywa oczekiwana z p̂. Zaznacz, że odpowiedź B obserwujemy tylko tam, gdzie B zobaczył A (G1).
**Z9.** (opcjonalnie, eksploracyjnie) „krzywa uczenia gustu": ile losowo odsłoniętych swipe'ów nowego nadawcy (k = 0, 5, 10, 20, 40) poprawia przewidywanie jego pozostałych swipe'ów; kolejność czasowa nie jest znana (tylko `day`), więc odsłaniaj losowo i napisz to wprost. Oraz „mapa gustów" (2D embeddingów odbiorców z M2 wytrenowanego na pełnych danych, kolor wg płci/pasma; kategorie < 5 nie kolorowane osobno) wraz z liczbą towarzyszącą: trafność przewidywania płci i pasma z embeddingu vs z samej popularności oraz stabilność mapy dla różnych ziaren. Podpis: „ilustracja, nie dowód".

## Metryki „plakatowe" (AUC nie jest nagłówkowe)

Dla osób nietechnicznych: AUC nie trafia na plakat. Zamiast niego:
1. **„O ile mniej niepewności"**: względna redukcja loglossu vs zgadywanie bazowe, słupki na drabinie modeli z CI.
2. **„Trafność wskazania 20% najlepszych profili"**: dla każdego nadawcy z ≥ 10 swipe'ami i 0 < prawych < wszystkich ułóż jego profile wg predykcji out-of-fold, weź górne 20% i policz odsetek faktycznie polubionych; porównaj z losowym wyborem (jego odsetek polubień) i z wyborem „po samej popularności" (M1 bez członu nadawcy). Raportuj zagregowany lift z CI (ważone Σ trafień / Σ wybranych). Zaznacz przybliżenie: wyniki z różnych foldów są łączone.
3. **Kalibracja** („gdy model mówi 30%, polubień jest 30%"): wykres niezawodności z pasmem CI.
4. **Oczekiwane vs zaobserwowane matche** (b), z CI i koszykami.
Wewnątrznadawcowe AUC („pojedynek dwóch profili") może zostać w tabelach pomocniczych pod tą nazwą, nie w nagłówkach.

## Dostarczane artefakty

1. `src/rentfriends/graph/` (dane, splity, modele, ewaluacja, wzajemność, hierarchia, wykresy) + testy.
2. Notebooki `graph_a_structure.ipynb`, `graph_b_reciprocity.ipynb`, `graph_c_hierarchy.ipynb`, uruchomione od zera.
3. `reports/graph/`: `numbers.json`, wykresy PNG+SVG w palecie ze STYLEGUIDE, `captions.md`: dla każdego wykresu jedno zdanie po polsku dla laika oraz linijka „czego to NIE znaczy".
4. `docs/graph/prereg.md`, `data-contract.md`, `open-questions.md`, `ai-disclosure.md` (co wykonał agent).

## Kryteria akceptacji

- prereg.md zacommitowany przed pierwszym uruchomieniem modeli M2–M4.
- Testy braku wycieku zielone; kolumn wyciekowych nie ma w żadnym zestawie cech.
- P1 i P2 raportowane razem; wniosek w tekście wynika z tabeli, nie z wyboru „ciekawszego" protokołu.
- Wyniki (b) i (c) opisane jako „zachowanie uwarunkowane ekspozycją", dopóki dostawca nie wyjaśni działania feedu (G1).
- Brak `bio` i `user_key` w repo i wynikach.
