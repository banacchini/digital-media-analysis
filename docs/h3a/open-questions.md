# H3a: otwarte pytania (po audycie, 2026-11-10)

1. **Flaga etykiety (Z1).** „Potwierdzony” = 95% CI wyklucza zero, a nie margines. Dolna granica OR
   (1,044) leży wewnątrz pasma pomijalności (do 1,105). Reguły nie zmieniono. Decyzja Dominika:
   czy w preprincie pisać „związek niezerowy, wielkość nierozstrzygnięta względem marginesu”.
   Wariant konserwatywny (przyjęty): flaga w summary.
2. **Odtworzenie liczb bazowych** pominięte na polecenie Dominika. Liczby M2/M3/lejka w tym
   przebiegu pochodzą z `reports/h3a/results.json`, a `audit_results.json` zgadza się z nimi
   (M2 OR 1,130; M3 1,189; N = 93 717). Nie uruchamiano ponownie GLMM GPBoost.
3. **Nie wykonano (P3):** Z6 (AUC-PR z bootstrapem dla M6), Z8 (emoji, `?`, język; model wtórny).
   Wariant do zrobienia: bootstrap po nadawcach na wagach krotności (jak w M6) i lokalne zliczanie
   znaków bez wyświetlania tekstu; język tylko offline.
4. **Notebook od zera** (`H3a-rendered.ipynb`, papermill) nie został ponownie wyrenderowany;
   audyt liczy się przez `rentfriends.h3a.audit.run_audit()` i `audit_plots`. Do zrobienia przed
   oddaniem: dodać komórkę z `audit_plots` i wyrenderować notebook (ok. 25-40 min).
5. **Grupa „O” (28 nadawców, 855 swipe'ów):** M2 OR 1,268 (0,905-1,776), M3 bez oszacowania.
   Nie do wnioskowania; klastrowanie dwukierunkowe przy 28 klastrach jest niewiarygodne.
6. **Cache** wcześniejszych poziomów leży w `reports/h3a/cache` (w gitcie); nowe fity w
   `data/interim/h3a/`. Nie przenoszono starych, żeby nie zmieniać historii wyników.
7. **Profil CI dla lme4** nie liczony (Wald + LRT p = 0,009); profil z GPBoost jest w B1.
