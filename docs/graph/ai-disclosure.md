# AI Disclosure — Graph Analysis Module

**Module:** `src/rentfriends/graph/` and associated notebooks / docs
**Date:** 2026-11-09
**Tool:** Antigravity (Claude Sonnet 4.6 Thinking), agy CLI
**Author / reviewer:** Jakub Smolarczyk

## What the agent did

1. Read and interpreted `docs/prompts/graph-stream-prompt.md` and related project docs.
2. Created the directory scaffold: `src/rentfriends/graph/`, `docs/graph/`, `reports/graph/`, `tests/graph/`.
3. Wrote all source files:
   - `data.py` — data loading, SHA-256 verification, sample funnel, feature engineering.
   - `splits.py` — P1 (edge-stratified), P2 (GroupKFold sender), pair-fold splits.
   - `models.py` — M0 (logistic), M1 (logistic + sender/receiver effects), M2 (MF), M3 (LightGCN), M4 (GraphSAGE).
   - `eval.py` — metrics (logLoss, AUC, lift@20%, calibration), bootstrap CI.
   - `reciprocity.py` — observed vs expected matches (b).
   - `hierarchy.py` — desire score (c), league curves.
   - `plots.py` — all figures in STYLEGUIDE palette.
   - `run_all.py` — orchestration script.
4. Wrote pre-registration document `docs/graph/prereg.md` **before** running any M2–M4 models.
5. Wrote `docs/graph/data-contract.md` and `docs/graph/open-questions.md`.
6. Generated test file `tests/graph/test_graph.py`.
7. Generated notebooks `notebooks/graph_a_structure.ipynb`, `graph_b_reciprocity.ipynb`, `graph_c_hierarchy.ipynb`.

## What the agent did NOT do

- Did not read, print, or use the `bio` column.
- Did not include `user_key` in any output file or figure.
- Did not access external APIs or scrape any website.
- Did not commit or push (per AGENTS.md rule 6).

## Human review required

- Verify all pre-registered choices (splits, hyperparameter grid, criteria) before running M2–M4.
- Run the notebooks end-to-end after human review; check that all tests pass.
- Review `docs/graph/open-questions.md` for items marked conservative.
- Confirm the 2-hour training cap (OQ9) is acceptable; if more time is available, revert epoch limits.

## Validation note

All AI-generated code was submitted to `ruff check` and `ruff format --check` before commit.
Tests in `tests/graph/test_graph.py` cover leak-check, split properties, and permutation baseline.
