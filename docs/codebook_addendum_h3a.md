# Codebook addendum: H3a

Propozycja dopisania do `docs/codebook.md`, część C (plik `codebook.md` nie był edytowany).
Format jak w części C. Zmienne liczone dla swipe'a A→B z wersji profilu as-of (D7,
`docs/h3a/decision-log.md` D-H3a-3/4). Implementacja: `src/rentfriends/h3a/variables.py`.

| Variable | Block | Definition | Source | Missing handling | Used in |
|---|---|---|---|---|---|
| `has_bio` | bio | `1 - bio_empty`; used in models so that OR > 1 supports H3a | `bio` | NULL bio = empty | H3a (M1-M3, M6) |
| `bio_empty_alt10` | bio | 1 if receiver's bio is NULL or shorter than 10 characters after `strip()` | `bio` | NULL = empty | H3a S5 |
| `bio_len_cap` | bio | 1 if `bio_len >= 250` (apparent field limit) | `bio` | 0 for empty bio | H3a M5 |
| `tag_count_receiver` | interests | receiver's effective tag count after mapping raw strings with `docs/interests_mapping.csv` (+ 4 Polish labels, D-H3a-6) and within-user dedup; in models: linear (standardised) + flag `== 0` (`tag_zero`) + flag `== 9` (`tag_cap`) | `interests` | empty list = 0 | H3a |
| `tag_count_raw` | interests | receiver's raw number of tag strings, no mapping or dedup; flags `tag_zero_raw`, `tag_cap_raw` | `interests` | empty list = 0 | H3a S6 |
| `profile_completeness_alt` | control | share of non-missing among 5 lifestyle fields (without `cleanliness`, `noise_level`, which may carry app defaults), receiver | Part A | empty string = missing | H3a S4 |
| `receiver_age_band` | control | receiver's age band, 27+ merged (18-20, 21-23, 24-26, 27+) | `age_band` | complete case | H3a S7 |

Uwagi:

- `same_sex` jest redundantne z `sex_pair` (wynika z niego w każdej z 9 komórek); w H3a używamy
  tylko `sex_pair`.
- `bio_empty`: definicja doprecyzowana jako „NULL lub długość 0 po `strip()`” (sam znak spacji
  lub nowej linii = puste).
- `bio_len`: liczone z tekstu po `strip()`. Rozbieżność z `bio_length` (G18) liczona względem
  surowej długości tekstu: 2,0% snapshotów odbiorców widzianych w swipe'ach.
- `profile_completeness`: puste napisy liczone jak braki. W S7 pomijane (kombinacja liniowa
  wskaźników „brak danych”).
- `same_city`: „unknown”, gdy którakolwiek strona ma `inne` lub brak miasta (także obie `inne`).
- Część C odwołuje się do „as-of rule from section 0”, której w codebooku nie ma; reguła jest w D7
  (`docs/prompts/m1-generation-plan.md`).
- Rozbieżności w repo (nie wpływają na H3a): mapowanie ma 67 kanonicznych slugów, a codebook D.1
  podaje 69; `tag_category_proposal.csv` ma 68 wierszy, w tym slugi `bussiness` i `often_outside`,
  których nie ma w mapowaniu (mapowanie ma `business`); w danych są 4 surowe ciągi spoza mapowania
  (D-H3a-6).
