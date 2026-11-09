# Data Contract v1 — Graph Analysis

Frozen input dataset for the graph analysis (read-only).

| File | SHA-256 | Notes |
|---|---|---|
| `data/processed/h1_analysis_dataset.parquet` | `1f0bb5b1e02e968772931b341655405b09a81f257ca90d3ff9f5862186d3f771` | Frozen; shared input from H1/H2/H3a pipeline |
| `data/processed/swipes.parquet` | *(read on first load; see `src/rentfriends/graph/data.py`)* | Raw swipes table, all types |
| `data/processed/users.parquet` | *(read on first load; see `src/rentfriends/graph/data.py`)* | Current user profiles |

## Contract rules

1. `h1_analysis_dataset.parquet` is **read-only**. The graph module reads it but never writes to it.
2. The SHA-256 above is verified at import time by `src/rentfriends/graph/data.py` and will raise
   `RuntimeError` if the file has changed.
3. Columns from `h1_analysis_dataset.parquet` that are **forbidden as features** (data leakage):
   `sender_right_rate`, `sender_total_swipes`, `is_extreme_user`, `is_low_activity`, `match`.
   These are computed on all swipes including test edges. Node-degree statistics used in models
   are always computed **inside each fold** from training edges only.
4. `bio` column from `users.parquet` is **never** read or used by the graph module.
5. No `user_key` values may appear in result files, figures, or reports (privacy).
   All outputs use internal integer node IDs or aggregate statistics.

## Sample filter funnel (target: graph training set)

| Step | Count | Note |
|---|---|---|
| All swipes in `swipes.parquet` | 116 414 | includes listings |
| Profile swipes (`target_type == 'profile'`) | 95 144 | matches prompt spec |
| Remove self-swipes | 95 144 | 0 self-swipes found |
| Available in `h1_analysis_dataset.parquet` (Hyderabad + other filters applied) | 94 295 | H1 pipeline filter |
| Graph training universe | 94 295 | starting point for graph splits |

Differences from the `95 144 → 94 295 → 93 717` funnel in the prompt:
- We use `h1_analysis_dataset.parquet` as the starting universe (94 295 rows) which already applies
  the Hyderabad filter and complete-case rules from the H1 pipeline.
- The final step of `93 717` from the prompt may refer to additional complete-case filtering on
  pair features; our graph module applies its own complete-case filter on pair feature columns
  within each fold, logged in `reports/graph/numbers.json`.
