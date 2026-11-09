# Kontrakt danych H1 v1 (2026-11-09)

Gałąź `fix/h1-rebase-v1`. Kod: `src/rentfriends/h1_v1.py` (budowa), `src/rentfriends/h1_tagval.py` (warianty decyzji o tagach),
`src/rentfriends/dataset_h1.py` (bez zmian w definicjach zmiennych). Testy: `tests/test_h1_v1.py`. Różnice (agregaty): `reports/h1/v1_diff_vs_v0.json`.
Zbiory leżą w `data/processed/` i **nie są w gitie**; tu są tylko ich sumy kontrolne.

## Sumy kontrolne (SHA-256)

| Plik | Rola | SHA-256 |
|---|---|---|
| `h1_analysis_dataset.parquet` | **v0**, mapowanie agenta, nienaruszony | `7d15f84be3d173c842d959470e3f14c0ae7ee625061dc27593b4abedb14bf8b4` |
| `h1_analysis_dataset_v1.parquet` | **v1**, decyzje końcowe (scenariusz (vi)) | `fdbc9d3ec8b86b8eb80179cb9a00df5d412755ebf556ae09dc16c27926b71463` |

Budowa v1 jest deterministyczna: dwa uruchomienia dają ten sam hasz (test `test_v1_build_is_deterministic_and_leaves_v0_untouched`).
Hasz v1 jest identyczny z haszem pliku `h1_analysis_dataset_consensus_merged.parquet`, zapisanego wcześniej przez `h1_tagval.run_impact` (ta sama ścieżka kodu, niezależne uruchomienie). Pliki `h1_analysis_dataset_consensus*.parquet` to artefakty walidacji tagów, nie kontrakt.
Przebudowa v0 z kodu (`h1_v1.build_v0`) daje te same kolumny i wartości co zapisany plik v0 (test `test_v0_rebuilds_from_code_and_v1_differs_only_in_tag_derived_columns`).

## Co oznacza v1

v1 = v0 z trzema decyzjami człowieka z walidacji tagów (`docs/tag-validation/decisions.md`), czyli **scenariusz (vi) z `reports/tag-validation/impact.md`**:

1. **Konsensus A** (raw → kanoniczny): `docs/tag-validation/consensus_A.csv`, nadpisania tam, gdzie decyzja różni się od mapowania agenta (8 mapowań surowych).
2. **Konsensus B** (kategoria kanonicznego tagu): `docs/tag-validation/consensus_B.csv` zamiast `proposed_category_claude` (5 różnic względem agenta: `cooking`, `instruments`, `vanlife` hobby → styl życia; `long_talks` `unclear` → styl życia; `city_breaks` hobby → `unclear`; w kodzie `unclear` trafia do zainteresowań jak hobby, więc ta ostatnia zmiana nie przesuwa żadnego tagu).
3. **Scalenia** z `docs/tag-validation/tag_merge_map.csv`: `quiet_evenings`, `peace_and_quite`, `silence_after_22` → `likes_calm`; `going_out_friends`, `often_outside` → `often_out`. Klucze D13 i grupy D15 przepięte na cel scalenia (kody D13 tych kluczy są identyczne, więc uzupełnianie pól się nie zmienia).

Bez zmian względem v0: lista swipe'ów i kolejność wierszy, wyniki `y_right`, `match`, wiek, płeć, miasto, statusy pól stylu życia, definicje zmiennych (w tym D15), wykluczenia (Hyderabad), reguła as-of (D7), próg rzadkich tagów (50).

## Różnice względem v0

| | v0 | v1 |
|---|---|---|
| kolumny | 49 | 49 (ten sam schemat) |
| wiersze (swipe'y po wykluczeniu Hyderabadu) | 94 295 | 94 295 |
| próba główna H1 (kompletne przypadki) | 92 754 | 92 754 |
| kolumny o zmienionej wartości | | `interests_set_sender`, `interests_set_receiver`, `interests_jaccard`, `interests_idf_jaccard`, `interests_shared_n`, `interests_count_sender`, `interests_count_receiver`, `interests_count_diff`, `interests_count_diff_abs`, `lifestyle_shared_tags_n`, `lifestyle_tag_conflict` |

Udział swipe'ów próby H1 ze zmianą (v1 względem v0; zgodnie z `impact.json`, scenariusz (vi)):

| Cecha | Udział swipe'ów |
|---|---|
| zmieniony zbiór zainteresowań (nadawca lub odbiorca) | 56,6% |
| zmieniony status zgodności któregokolwiek z 7 pól stylu życia lub kierunek palenia | 0,0% |
| zmieniona liczba wspólnych tagów stylu życia | 16,5% |
| zmieniony konflikt D15 | 0,09% (86 swipe'ów, wszystkie z 0 → 1) |

Średnie na próbie H1 (v0 → v1): Jaccard zainteresowań 0,0667 → 0,0633; liczba wspólnych hobby 0,388 → 0,319; liczba hobby nadawcy 2,95 → 2,56; liczba wspólnych tagów stylu życia 0,934 → 1,099; odsetek konfliktów D15 52,32% → 52,41%.
Źródło mechanizmu: tagi przeniesione z hobby do stylu życia (`cooking`, `instruments`, `vanlife`, `long_talks`) opuszczają zainteresowania i wchodzą do tagów stylu życia, a scalenia `likes_calm` zwiększają liczbę wspólnych tagów stylu życia.

## Użycie

```python
from rentfriends import h1_v1
h1_v1.write_v1()          # buduje data/processed/h1_analysis_dataset_v1.parquet (nigdy nie zapisuje v0)
df = h1_v1.load_v1()      # czyta v1 i dodaje city_same / city_diff
```

D15 (anomalia 52% konfliktów): wyjaśniona jako prawdziwa prewalencja, definicja bez zmian (`docs/h1/d15-conflict-investigation.md`).
