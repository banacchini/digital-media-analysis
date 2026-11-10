# H3a: otwarte pytania (po audycie, 2026-11-10)

1. **Flaga etykiety (Z1).** „Potwierdzony” = 95% CI wyklucza zero, a nie margines. Dolna granica OR
   (1,044) leży wewnątrz pasma pomijalności (do 1,105). Reguły nie zmieniono. Decyzja Dominika:
   czy w preprincie pisać „związek niezerowy, wielkość nierozstrzygnięta względem marginesu”.
   Wariant konserwatywny (przyjęty): flaga w summary.
2. **Odtworzenie liczb bazowych** pominięte na polecenie Dominika. Liczby M2/M3/lejka w tym
   przebiegu pochodzą z `reports/h3a/results.json`, a `audit_results.json` zgadza się z nimi
   (M2 OR 1,130; M3 1,189; N = 93 717). Nie uruchamiano ponownie GLMM GPBoost.
3. **P3 wykonane (2026-11-10):** Z6 (AUC-PR z bootstrapem po nadawcach) i Z8 (emoji, `?`,
   język; model wtórny bez werdyktu). Język to własna heurystyka stop-słów (brak lokalnej
   biblioteki bez zmiany `pyproject.toml`), **nieprzetestowana** względem wzorca człowieka;
   traktować jako opis, nie instrument pomiarowy.
4. **Notebook** (`H3a.ipynb`, poziom 3, papermill) wyrenderowany do
   `notebooks/H3a-rendered.ipynb` z sekcjami 12-13 (audyt, summary). Ciężkie fity (GPBoost,
   lme4, sanity check) szły z cache po haszu danych (poprzednio policzone na tych samych danych
   i z tym samym ziarnem); przeliczono M6 (zmiana kodu: AUC-PR), cache M6 usunięto. ΔAUC M6
   odtworzone: 0,00343.
5. **Grupa „O” (28 nadawców, 855 swipe'ów):** M2 OR 1,268 (0,905-1,776), M3 bez oszacowania.
   Nie do wnioskowania; klastrowanie dwukierunkowe przy 28 klastrach jest niewiarygodne.
6. **Cache** wcześniejszych poziomów leży w `reports/h3a/cache` (w gitcie); nowe fity w
   `data/interim/h3a/`. Nie przenoszono starych, żeby nie zmieniać historii wyników.
7. **Profil CI dla lme4** nie liczony (Wald + LRT p = 0,009); profil z GPBoost jest w B1.
8. W `notebooks/H3a-rendered.ipynb` usunięto osadzone PNG (limit 1000 kB w hooku `check-added-large-files`);
   rysunki są w `reports/h3a/figures/` i `reports/h3a/audit/`, a ich dane w `figure_data/`.
