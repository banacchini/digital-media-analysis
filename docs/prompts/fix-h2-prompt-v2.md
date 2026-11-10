# Prompt (v2): naprawa H2 po audycie

## Rola i kontekst

Pracujesz w repo RentFriends (kurs AMC, PWr). H2: *płeć (i wiek) nadawcy i odbiorcy wpływają na prawy swipe*. Kod: `rentfriends.h2`, notebook `h2_demographics.ipynb` (ścieżki potwierdź `ls`/`grep`). Stan repo: `main` zawiera już audyt H1, walidację tagów i H1 na kontrakcie danych v1 (`docs/data-contract-v1.md`, `docs/h1/h1-summary.md`, `docs/h1/rebase-v1-2026-11-09.md`).

Przeczytaj najpierw: `docs/prompts/m1-generation-plan.md` (D6–D18), `docs/codebook.md`, `rentfriends_hipotezy_karta_eksploracji.md` (H2, G1–G18), `STYLEGUIDE.md`, `data/README.md`, `docs/h1/h1-summary.md`. Moduł `rentfriends.h3a` ma działające opakowania GLMM (GPBoost) i cross-check lme4 (R): możesz je **importować i wywoływać**, nie modyfikować. Z H1 możesz importować (tylko do odczytu) `age_direction_check` z `rentfriends.h1_audit`.

Audyt wykazał problemy niżej. **Traktuj każde twierdzenie jako hipotezę do sprawdzenia, w tym liczby z rachunków orientacyjnych.** Jeśli się nie potwierdza, napisz to w changelogu.

## Zasady nadrzędne

1. **Ten prompt jest wyraźną prośbą o commity** na gałęzi `fix/h2-audit` (utwórz od aktualnego `main`; jeśli taka gałąź już istnieje, użyj `fix/h2-audit-2`). Małe opisowe commity (jeden krok = jeden commit), bez squashowania; testy i `ruff` przed commitem. Nie commituj niczego z `data/` ani `data/interim/`. Nie dotykaj `uv.lock` i `pyproject.toml`.
2. **Środowisko:** wyłącznie `uv run --frozen`, nigdy `uv run --active`. **Nie używaj `pkill`/`killall`** (poprzednia sesja zamknęła cudze jądra Jupytera); procesy, które sam uruchomiłeś, zatrzymuj po PID. Nic poza katalogiem repo.
3. **Najpierw odtwórz liczby** (tolerancja po zaokrągleniu do podanej precyzji): macierz stawek F→F 0,200; F→M 0,085; M→F 0,296; M→M 0,199; OR surowy F 2,645 i M 0,602; OR z kontrolami F 2,439 i M 0,657; CV AUC (płeć 0,603; płeć + wiek 0,620). Rozbieżność → zatrzymaj się i opisz w `docs/h2/open-questions.md`.
4. **Nie dobieraj specyfikacji pod wynik.** Każdą zmianę oznacz w changelogu: `pre-rejestrowana` albo `post hoc (audyt)`. Raportuj wszystkie warianty. H2 pozostaje **eksploracyjne** (macierz płci widziano przed sformułowaniem hipotezy, D17).
5. **Prywatność (G12):** `bio` w ogóle nie wczytujesz; tylko agregaty; komórki < 5 użytkowników tłumione; żadnych zewnętrznych API; bez `user_key` w wynikach.
6. Nie modyfikuj `rentfriends.h1`, `h3a`, `graph`, `h3b`. Ciężkie obliczenia (GLMM, bootstrap) zapisuj w cache `data/interim/h2/` (poza gitem, klucz = hasz danych), żeby zmiana wykresów nie wymagała przeliczeń; cache nie śledzi zmian kodu, więc po zmianie kodu usuń odpowiedni plik.
7. Niejednoznaczne decyzje: `docs/h2/open-questions.md`, wariant konserwatywny z adnotacją.

**Poziomy priorytetu (czas jest ograniczony):** **P1** = Z1, Z2, Z7; **P2** = Z3, Z4; **P3** = Z5, Z6. Jeśli czas lub zasoby się kończą, zatrzymaj się po P1+P2, zapisz niewykonane P3 w `open-questions.md` i dokończ dokumentację.

## Zadania

**Z1 (P1). Popularność profili vs premia za własną płeć.** Notebook twierdzi, że „z tych danych nie umiemy ich rozdzielić". Wstępny rachunek z surowych stawek (bez kontroli i klastrowania) sugeruje, że to możliwe przy założeniu, że popularność profili kobiet i premia za własną płeć są takie same dla obu płci nadawców: efekt odbiorcy F vs M ≈ 0,76 logitu (OR ≈ 2,1), premia za własną płeć ≈ 0,22 (OR ≈ 1,25). **Zweryfikuj modelem.** Identyfikacja: w tabeli 2×2 (nadawca F/M × odbiorca F/M) z efektami nadawcy i odbiorcy identyfikowany jest **jeden** kontrast interakcyjny; osobnych premii per płeć nadawcy nie raportuj jako zidentyfikowanych. Zrób: (a) GLMM z crossed random intercepts (nadawca, odbiorca) z jednym członem interakcji `sender_F × receiver_F`: log-OR z CI; (b) model z efektami stałymi nadawcy i `receiver_is_F` jako efektem głównym (popularność profili kobiet; zaznacz, że to cecha odbiorcy skorelowana z innymi); (c) jawne założenie identyfikacyjne w tekście wyniku; (d) płeć `O` poza modelem głównym (G16).

**Z2 (P1). Efekt wieku.** (a) Macierz nadawca × odbiorca (pasma 18–20, 21–23, 24–26, 27+) z odsetkiem prawych i CI po nadawcach, komórki < 5 tłumione; (b) model `same_band`, `age_band_diff_abs`, `age_band_diff` (ze znakiem; dla nadawców 18–20 różnica nie bywa ujemna) oraz wrażliwość z efektami stałymi pasma nadawcy; (c) OR z CI dla składników. **Spójność z H1:** użyj tej samej specyfikacji i `age_direction_check`; w H1 (v1) OR starszy o 1 pasmo ≈ 0,62 [0,57; 0,68], starszy o 2+ ≈ 0,35 [0,29; 0,43], młodszy o 1 ≈ 0,97 [0,87; 1,09]. Różnice względem H1 (inne próby: 93 717 vs 92 754; inne kontrole) wyjaśnij liczbami.

**Z3 (P2). Estymator zgodny z D18.** Dla modeli Z1 i Z2 dopasuj GLMM (opakowania z `h3a`; fallback przy braku zbieżności lub SE: pooled logit z klastrowaniem dwukierunkowym) i **zawsze zapisz, który estymator dał liczbę**. Tabela obok siebie: OR populacyjne (pooled) vs warunkowe (GLMM), z komentarzem (przy wariancji efektu nadawcy ≈ 7,8 różnica jest duża i nie wolno porównywać OR z różnych estymatorów bez zastrzeżenia).

**Z4 (P2). Metryki i walidacja.** AUC-PR w CV; CV grupowane po odbiorcach jako drugi widok (obecne kontroluje przeciek tylko po nadawcach); sparowane różnice ΔlogLoss/ΔAUC z CI (bootstrap predykcji out-of-fold po nadawcach), nie samo odchylenie między foldami.

**Z5 (P3). Wrażliwość.** Do 6 scenariuszy dodaj: bez miasta „inne" (G6); tylko swipe'y `both_prior_version` (jeśli flaga dostępna); model z korelatami z H1 jako dodatkowymi kontrolami, czytanymi **tylko do odczytu z `h1_analysis_dataset_v1.parquet`** (`lifestyle_agree_ratio`, `interests_idf_jaccard`; **nie** `lifestyle_tag_conflict`, bo ma prewalencję ~52% równą przypadkowi): czy OR płci się zmienia (w tym próba 92 754 vs 93 717; opisz). Oszacuj wpływ ~50% swipe'ów z `first_version` (as-of).

**Z6 (P3). `y_match`.** Poziom par (uniwersum 7790 par z decyzją obu stron, 487 matchy): opis z CI i model oszczędny (≤ 8 zmiennych); 246 matchy z jednym swipe'em (G15) poza analizą główną, w wrażliwości dopisane jako matche.

**Z7 (P1). Wniosek (sekcja 7), podsumowanie i notebook.**
- Zastąp „nie umiemy ich rozdzielić" wynikiem Z1 z założeniem identyfikacyjnym i zastrzeżeniem: korelacja, nie preferencja; zachowanie **uwarunkowane ekspozycją** (G1: feed nieznany).
- Usuń sekcję „Czego nie oszacowaliśmy" dla wieku po Z2.
- Nagłówek spójny z H1: *prawy swipe przewidują głównie para płci i wiek odbiorcy względem nadawcy; ocena jest warunkowa na ekspozycji.*
- Wielkości efektów w jednostkach zrozumiałych dla laika (p.p., OR, które OR: populacyjne czy warunkowe), nie tylko ΔLL.
- Podział konfirmacyjne/eksploracyjne/post hoc; ograniczenia (płeć `O`, ekspozycja, wąska próba 18–20, as-of).
- Aktualizuj tablicę dowodów i podsumowanie; notebook uruchomiony od zera, deterministycznie (ziarno bez zmian).

## Dokumentacja i artefakty

`docs/h2/audit-fixes-2026-11-09.md` (tabela *problem → ustalenie → zmiana → liczby przed → po → pre-rejestrowane/post hoc*; sekcja „ujawnienie użycia AI" z incydentami), zaktualizowane `docs/h2/open-questions.md`, kod z testami (dekompozycja interakcji, macierz wieku, estymatory), notebook z wynikami, wykresy w palecie `STYLEGUIDE.md` z jednozdaniowymi podpisami po polsku. Przypomnienie dla człowieka: wyeksportować pełny log sesji do `logs/ai/`.

## Kryteria akceptacji

- Liczby sprzed zmian odtworzone; każda zmiana wyniku wyjaśniona zmianą kodu.
- Dla każdego raportowanego OR podany estymator (GLMM / pooled / fallback).
- Z1 zawiera jawne założenie identyfikacyjne; osobne `h_F`, `h_M` nie są raportowane jako zidentyfikowane.
- Wyniki wieku spójne z H1 lub różnica wyjaśniona.
- Każdy wniosek w sekcji 7 ma liczbę z CI w notebooku; język bez przyczynowości.
- Brak `bio`, `user_key`, wierszy tabel w repo i wynikach; brak zmian w `uv.lock`; brak `uv run --active` i `pkill`.
