# H1: naprawy po audycie (2026-11-08)

Gałąź `fix/h1-audit`. Wykonawca: agent Claude Code (patrz sekcja „Ujawnienie użycia AI”), review człowieka: `[DO ZROBIENIA]`.
Kod: `src/rentfriends/h1.py`, `src/rentfriends/h1_audit.py`, `src/rentfriends/dataset_h1.py`; notebook: `notebooks/h1-hypothesis.ipynb`
(wersja z wynikami: `notebooks/h1-hypothesis-rendered.ipynb`, uruchomiona od zera, ziarno 42). Otwarte decyzje: `docs/h1/open-questions.md`.

Traktowano każde twierdzenie audytu jako hipotezę do sprawdzenia. Poniżej: co się potwierdziło, co nie, co zmieniono.

## 0. Odtworzenie liczb sprzed zmian

Odtworzone na danych lokalnych specyfikacją `spec_old` (asercja w notebooku, sekcja 6.1): n = 92 754; ΔLL styl życia = 41,379 (raportowane 41,38);
ΔLL wiek+zainteresowania = 739,144 (739,14); CV AUC null / styl życia / wiek+zainteresowania / pełny = 0,500 / 0,519 / 0,581 / 0,584. Brak rozbieżności.

## 1. Tabela: problem → ustalenie → zmiana → liczby przed/po → status

Skróty: ΔLL(S) = przyrost stylu życia ponad wiek+zainteresowania; ΔLL(W+Z) = przyrost wieku+zainteresowań ponad styl życia (jako ostatnie bloki).
Liczby „po” każdego wiersza to stan po danej zmianie, **skumulowanie** (Z1 → Z2 → Z3).

| Zad. | Problem (audyt) | Co znalazłem | Co zmieniłem (commit) | Liczby przed → po | Status |
|---|---|---|---|---|---|
| Z1 | `lifestyle` ma `n_vars=5`, reszta 6/8/11: brakuje kontroli | **Częściowo potwierdzone.** `lifestyle` (3 zm. + 2 miasto) nie miał ani kontroli płci, ani bloku wieku; `demog` i `age_interests` miały `same_sex`. Brakowało więc więcej niż jednej zmiennej. | `H1Spec`: kontrole identyczne we wszystkich 8 podzbiorach bloków, jedna próba kompletnych przypadków (`df69b8d`) | ΔLL(S) 41,38 → 41,38; ΔLL(W+Z) 739,14 → 731,20 | post hoc (audyt) |
| Z2 | `same_sex` nie oddaje asymetrii F→M / M→F | **Potwierdzone** (patrz OR w notebooku 6.2: `sex_F_M` 0,42, `sex_M_F` 1,66). | 8 dummies `sex_pair` (ref. F→F) jako kontrola; `LEGACY_SPEC` = `spec_old`, `SAME_SEX_SPEC` jako wrażliwość (`59cc22d`) | ΔLL(S) 41,38 → 45,93; ΔLL(W+Z) 731,20 → 406,00 | post hoc (audyt) |
| Z3 | `age_band_diff` czytany jako „preferencja podobnego wieku” | **Potwierdzone.** To kierunek. Młodszy o 1 pasmo vs to samo pasmo (FE pasma nadawcy): OR 0,97 [0,87; 1,09]; starszy o 1: 0,62 [0,57; 0,68]; starszy o 2+: 0,35 [0,29; 0,43]. Kontrast w obrębie pasm: tylko 24-26 ma +4,3 pp [0,4; 8,5], 21-23 i 27+ bez różnicy. Pasmo 18-20 nie ma ujemnych różnic. | Blok wieku: `same_band`, `age_band_diff_abs`, `age_band_diff`; wrażliwość: `+|diff|²`, FE pasma nadawcy; `age_direction_check` (`cf011ce`) | ΔLL(S) 45,93 → 40,46; ΔLL(W+Z) 406,0 → 545,0. Wrażliwość: `+|diff|²` 40,39 / 557,6; FE pasma 38,50 / 372,6 | `|diff|²`: pre-rejestrowana (karta 3.2), poza głównym modelem; reszta post hoc |
| Z4 | `demog → age_interests` tylko ≈ 10,6, `age_interests → full` 41,4: co dominuje? | **Potwierdzone** dla `spec_old` (10,61 i 41,38). Po poprawkach: średni ΔLL po 6 kolejnościach: wiek 533,2; styl życia 42,5; zainteresowania 13,9 (dLL/df 177,7 / 14,2 / 4,6). Dominuje **wiek**; zainteresowania są najsłabsze. | `block_increment_table`: pierwszy / ostatni / średnia (Shapley), dLL/df, dAIC (`b2033ea`) | „dominacja wieku i zainteresowań” → dominacja samego wieku | post hoc (audyt); porównanie z karty zachowane |
| Z5 | Brak CI różnicy przyrostów; CV bez sparowanych różnic i AUC-PR | Brak (potwierdzone). Kryterium H1 **nie spełnione**: ΔΔLL(S − W+Z) = −504,5, konserw. CI [−883,4; −300,8] (szerszy: nadawcy); S − wiek −487,8 [−845,8; −273,3]; S − zainteresowania +27,0 [−59,3; 106,4]. CV (ostatni blok, S − W+Z): logloss −0,0053 [−0,0087; −0,0021], AUC −0,0224 [−0,0330; −0,0117], AUC-PR −0,0310 [−0,0499; −0,0164]. | `fit_logit_fast`, `bootstrap_model_loglik` (B = 1000, ziarno 42, po nadawcach i odbiorcach), `combine_cluster_cis`, `oof_predictions`, `paired_cv_differences`; AUC-PR w `grouped_cv_h1` (`55cffbb`, `c06f0e8`) | nowe wielkości | kryterium: pre-rejestrowane; implementacja post hoc |
| Z6a | Brak IDF-Jaccarda | Dodany: `interests_idf_jaccard`. Prawie nie zmienia wyniku. | `idf_weights`, `weighted_jaccard`, `user_tag_idf` (`8611dda`, `7869175`) | ΔLL(S) 40,46 → 40,44; ΔLL zainteresowań (ostatni) 13,5 → 14,3 | pre-rejestrowana (karta 3.2) |
| Z6b | Brak baseline'u losowych par | Prawe: Jaccard 0,0694 vs permutacje 0,0652 [0,0637; 0,0666]; lewe 0,0654 vs 0,0658. Różnica prawe − lewe 0,0040, CI po nadawcach [−0,0021; 0,0104] obejmuje 0 (p permutacyjne = minimum 1/501 jest zbyt optymistyczne: brak klastrowania). | `interests_permutation_baseline` (permutacja w obrębie równej liczby tagów), `permute_within_strata`; kalibracja sprawdzona symulacyjnie (sd z = 1,06 przy 200 zbiorach) (`8611dda`) | nowe | pre-rejestrowana (karta 4) |
| Z6c | Sufit 9 tagów | Po oczyszczeniu tagów (hobby) sufit 9 prawie nie występuje (max 9 nadawca / 8 odbiorca). Surowa liczba tagów = 9 dotyczy 82,9% swipe'ów (profil którejkolwiek strony). Kontrola `interests_at_cap` nie zmienia wniosku. | `interests_at_cap`, `H1Spec.cap_control` | ΔLL(S) 40,46 → 39,56 | post hoc (audyt) |
| Z7 | Per pole, braki, `fillna(0)` w tercylach | `fillna(0)` mieszał 965 wierszy bez danych z niską zgodnością (odsetek prawych w „brak danych” 12,1% vs 20,2% w niskiej). Po Holmie żadne pole nie jest istotne (min p_holm 0,57, `cleanliness`); naiwne ΔLL zawyża (np. `work_from_home` 54,1, Wald p = 0,26). Palenie: niepalący → użytkownik OR 0,86 [0,78; 0,95]; użytkownik → niepalący 0,94 [0,68; 1,29]; symetria p = 0,65. | `per_field_analysis`, `field_dummies`, `holm_adjust`, tercyle przez `lifestyle_agree_groups` zamiast `qcut(fillna(0))` (`f901439`) | nowe | eksploracyjna (D16: analiza per pole drugorzędna); Holm zgodnie z zadaniem |
| Z8a | Dodać „bez miasta inne” i `spec_old` | Dodane (12 scenariuszy). ΔLL(S) w zakresie 29,0–66,1; ΔLL(W+Z) 353,6–889,9. | `sensitivity_analysis_h1` + kolumna `status` (`b95350c`) | 5 → 12 scenariuszy | G6, D6, D7, `|diff|²`, IDF: pre-rejestrowane; `spec_old`, `same_sex`, FE pasma, sufit: post hoc |
| Z8b | Dlaczego 92 754 ≠ 93 330 ≠ 93 717 | Jeden lejek: 116 414 → 95 144 (−21 270 swipe'ów na ogłoszenia) → 94 295 (−849 Hyderabad) → 93 717 (−578 bez pasma wieku; to próba H2/H3a) → **92 754** (−963 bez żadnego wspólnie znanego pola stylu życia; to próba H1). 93 330 w starym lejku to błąd: krok sprawdzał `same_band`, które nigdy nie jest NaN (brak pasma → 0). | `sample_funnel` (`b95350c`) | 93 330 → usunięty | — |
| Z9 | Walidacja normalizacji tagów (κ) | Raport **nie istnieje** (sprawdzono pliki, historię i wszystkie gałęzie). Kodeks część D to tylko plan. Zgodność propozycji Claude vs Gemini 58/68 (85,3%) to nie walidacja. **Nie podano żadnego κ.** | Lista zadań w `docs/h1/open-questions.md`, sekcja 3 | — | — |
| Z10 | Sekcja „Wniosek” | Przepisana: wiek jako kierunek (E6), dominacja wieku z CI zamiast „wieku i zainteresowań” (E2–E4), usunięte twierdzenia o zdjęciu i przewijaniu (hipoteza niezweryfikowana), zastrzeżenie o rozdzielczości pomiaru (G14), podział konfirmacyjne / eksploracyjne, tablica dowodów E1–E11 generowana w notebooku. | notebook | H1 niepotwierdzona (kryterium z karty nie spełnione) | — |

Dodatkowo: `G12` — tłumienie komórek par płci z < 5 użytkownikami (`sex_pair_user_counts`, `mask_small_cells`, `8c1ba42`); `load_h1_data` i `load_user_idf` wyszukują `docs/` obok `data/`, więc działają z `notebooks/` (`117f3a5`); cache `h1_analysis_dataset.parquet` jest przebudowywany, gdy brakuje nowych kolumn.

## 2. Schemat zbioru

Kolumny **dodane** (nic nie usunięto): `interests_idf_jaccard`, `raw_tags_n_sender`, `raw_tags_n_receiver`, `interests_at_cap`, `interests_set_sender`, `interests_set_receiver`,
`lsf_daily_routine`, `lsf_lifestyle`, `lsf_work_from_home`, `lsf_cleanliness`, `lsf_noise_level`, `lsf_smoking`, `lsf_alcohol`, `smoking_direction`.
Kolumny `same_band`, `age_band_diff_abs` i inne dotychczasowe bez zmian. Zbiór jest poza gitem; kolumny `interests_set_*` zawierają kanoniczne tagi hobby (kategorie), nie tekst użytkownika; brak pól `bio`.

## 3. Testy i lintery

Nowe testy: `tests/test_h1_audit.py` (bootstrap CI, permutacja, IDF-Jaccard w `tests/test_dataset_h1.py`, bloki, wiek, per pole, Holm, lejek, tłumienie komórek), rozszerzone `tests/test_h1.py`.
`ruff check`, `ruff format` i `pytest` uruchamiane przed każdym commitem (pre-commit). Pełny zestaw: wszystkie testy przechodzą poza 3 testami `tests/test_eda.py`, które failują także bez moich zmian (brak lokalnego `data/tables_metadata.json`).

## 4. Zmiana wniosku

Wniosek „H1 nie została potwierdzona” **nie zmienia się**, ale zmienia się jego uzasadnienie: wcześniej „dominują wiek i zainteresowania” (czytane przez znak różnicy wieku jako „podobny wiek”), teraz „dominuje wiek (jako kierunek: kara za starszego odbiorcę), zainteresowania są najsłabsze, a styl życia jest słabym sygnałem bez mierzalnego zysku poza próbą”.
Kryterium z karty (CI różnicy przyrostów) jest spełnione w kierunku przeciwnym do H1. Wniosek jest taki sam we wszystkich 12 scenariuszach wrażliwości.

## 5. Ujawnienie użycia AI

- **Narzędzie / model:** Claude Code (Claude Sonnet 5.5), sesja 2026-11-08/09, uruchomiona przez Dominika (banacchini) na podstawie promptu „naprawa H1 po audycie”. Log sesji: `logs/ai/claude/banacchini/2026-11-09-003547-pastedcontent-id9f5b.txt` (eksport dotyczy części sesji; pełny log do wyeksportowania przez osobę uruchamiającą, `logs/ai/README.md`).
- **Zadania wykonane przez agenta:** weryfikacja twierdzeń audytu w kodzie i danych (Z1–Z9); napisanie testów i kodu (`h1.py`, `h1_audit.py`, `dataset_h1.py`, testy); uruchomienia na danych lokalnych (bootstrap, CV, permutacje, sprawdzenie kalibracji baseline'u); wygenerowanie i uruchomienie notebooka; napisanie `docs/h1/open-questions.md`, tego dokumentu i sekcji „Wniosek”; drobne commity na `fix/h1-audit`.
- **Nie dotyczy `bio`:** agent nie czytał, nie wyświetlał ani nie przetwarzał treści `bio`; do notebooka i do tego dokumentu trafiły wyłącznie agregaty.
- **Incydenty:** (1) agent uruchomił `uv run --active`, co usunęło i odtworzyło `/home/dominik/.venv` (nie środowisko projektu); (2) `uv run` przeliczył `uv.lock`, zmianę cofnięto i użyto `--frozen`; (3) jeden commit odrzucił hook lintera (zbyt długa linia), poprawiono i zacommitowano ponownie.
- **Co zweryfikował człowiek:** `[DO ZROBIENIA]` — review kodu i wniosków, akceptacja decyzji z `open-questions.md`. Do tego czasu liczby i wnioski są wynikiem pracy agenta, sprawdzonym testami i odtworzeniem liczb sprzed audytu, ale nie przeglądem człowieka.
- **Instrument AI w analizie:** bez zmian względem `docs/ai-disclosure.md` (klasyfikacja tagów, D11/D19); walidacja względem człowieka nadal nie wykonana (`open-questions.md`, sekcja 3).
