# Pre-registration — Graph Analysis of Swipe Network

**Filed:** 2026-11-09
**Branch:** feat/graph
**Status:** LOCKED — changes after first M2–M4 run must be added as dated `post hoc` entries.

---

## 1. Research questions

**(a) Graph structure information.**
Does the swipe-graph structure carry information about `y_right` beyond pair-level features and
node propensities (sender generosity, receiver popularity)?

**(b) Reciprocity beyond propensities.**
Does the number of matches among pairs where both decisions are recorded exceed the count expected
under independence (∑ p̂_AB · p̂_BA)?

**(c) Hierarchy of desire.**
Following Bruch & Newman (2018, *Science Advances*), is there evidence of "leagues" (desire
hierarchy) in the swipe graph? Does reciprocity decay with desire-rank difference?

---

## 2. Unit of analysis

- Primary: directed swipe edge A→B (sender A, receiver B).
- Secondary (b, c): unordered pair {A, B} with both decisions recorded.

---

## 3. Sample definition

Starting universe: `h1_analysis_dataset.parquet` (94 295 rows).
This file already applies the Hyderabad filter and complete-case rules from the H1 pipeline
(see `docs/graph/data-contract.md`).
No additional exclusions in the main analysis.
Sensitivity: without extreme-activity users (`is_extreme_user == True`).

**Bipartite graph:** senders and receivers are distinct node sets, even when the same user
appears in both roles (two-node representation per user).

---

## 4. Features

**Pair features (from frozen parquet, never computed on test edges):**

| Column | Type | Missing handling |
|---|---|---|
| `sex_pair` | categorical → one-hot | none missing |
| `same_band` | binary | 0 |
| `age_band_diff` | numeric (signed) | 0 + missing indicator |
| `age_band_diff_abs` | numeric | 0 + missing indicator |
| `same_city` | binary | 0 |
| `city_diff` | binary (derived) | 0 |
| `interests_jaccard` | numeric [0,1] | 0 + missing indicator |
| `interests_shared_n` | integer | 0 |
| `lifestyle_agree_ratio` | numeric [0,1] | 0 + missing indicator |
| `lifestyle_tag_conflict` | binary | 0 |
| `lifestyle_shared_tags_n` | integer | 0 |

Standardisation: z-score from training-fold statistics only (no leakage from test).

**Forbidden columns (leakage):** `sender_right_rate`, `sender_total_swipes`,
`is_extreme_user`, `is_low_activity`, `match`. Never used as features.

**Node features (M4 only):** `sex`, `age_band`, `city`, multi-hot interests, lifestyle fields.
Computed from `users.parquet` joined to sender/receiver `user_key` **before** fold splitting
(these are static profile features, not label-derived).

---

## 5. Model ladder

All models predict `y_right` (binary), trained with BCE loss.

| Model | Description | Features |
|---|---|---|
| **M0** | Logistic regression | Pair features only |
| **M1** | Logistic + sender + receiver one-hot (L2 regularised) | Pair features + node effects |
| **M2** | M1 + bilinear MF term: logit = b + a_s + c_r + u_s·v_r + w·x | Pair features + latent factors |
| **M3** | LightGCN bipartite (separate relations: right/left swipes), head = M2 | Graph propagation |
| **M4** | GraphSAGE with node features (inductive), aggregation head | Node features + graph |

**Primary contrast (a):** best of M2–M4 (chosen on training folds) vs M1.

---

## 6. Hyperparameter grid (fixed, ≤ 6 configs for 2-hour cap)

| Parameter | Values |
|---|---|
| Embedding dim `d` | 8, 16, 32 |
| L2 weight | 1e-4, 1e-3 |
| GNN layers | 1, 2 |

Grid: `d ∈ {8, 32} × L2 ∈ {1e-4, 1e-3} × layers ∈ {1, 2}` = 8 configs (≤ 12 from spec;
reduced to 6 effective by layers only applying to M3/M4).
Optimiser: AdamW, full-batch.
Max epochs: **100** (reduced from 300 due to MPS device and 2-hour cap; see OQ9 in
`docs/graph/open-questions.md`).
Early stopping: patience 20 on internal validation (10% of training edges, random within-sender).
Random seeds: 5 seeds (42, 123, 7, 2024, 1337).

> **Post-hoc addendum (2026-11-09):** Max epochs reduced from 300 to 100 and effective grid
> reduced to 6 configs due to user-specified 2-hour training cap and MPS-only device.
> This change was registered before any M2–M4 run.

---

## 7. Splits

### P1 — Transductive (edge-stratified by sender)

5-fold CV. Each sender's edges are randomly assigned to one of 5 folds (stratified by `y_right`).
Evaluation on test edges where both sender and receiver have ≥ 5 training edges.
Report fraction of edges excluded.

### P2 — Cold-start (GroupKFold by sender)

5-fold `GroupKFold` on sender ID. In fold, M1 drops sender effects (receiver effects only).
M3 is not evaluated in P2 (transductive by design). M4 is evaluated inductively.

### Folds for (b) and (c)

Folds defined on **unordered pair {A, B}**: both directed edges of a pair always fall in the
same fold. This ensures p̂_AB and p̂_BA are cross-fitted and neither saw the other's label
during training.

Universe for (b): unordered pairs where both A→B and B→A appear in h1 (empirically ~7 772 pairs).

---

## 8. Decision criterion

**Graph structure "contributes" if:**
- ΔlogLoss (best M2–M4 minus M1) ≤ −0.002, **and**
- Bootstrap 95% CI of ΔlogLoss does not include 0.

If CI excludes 0 but |Δ| < 0.002: "statistically detectable, practically negligible."

**Negative result** (Δ ≈ 0 or positive) is a full, valid conclusion.

---

## 9. Uncertainty

- Bootstrap by **sender** on out-of-fold predictions (paired logLoss differences).
- Second view: bootstrap by **receiver**; report the wider CI as the conservative one.
- For (b) and (c): node bootstrap (sample users, retain induced pairs).
- Bootstrap replicates: 1 000.

---

## 10. Power simulation (Z5)

Generate labels on actual graph structure (node degrees, exposures) using M1 as ground truth
plus a latent factor of increasing strength λ ∈ {0, 0.1, 0.2, 0.5, 1.0}.
Repeat 100 times per λ. Report minimum detectable effect (MDE) = smallest λ where the pipeline
detects structure at 80% power (Δ < −0.002 and CI excludes 0).
At λ = 0, false-alarm rate should be ≈ 5%.

---

## 11. Output artefacts

| Artefact | Path |
|---|---|
| Package | `src/rentfriends/graph/` |
| Notebooks | `notebooks/graph_a_structure.ipynb`, `graph_b_reciprocity.ipynb`, `graph_c_hierarchy.ipynb` |
| Numbers | `reports/graph/numbers.json` |
| Figures | `reports/graph/*.png`, `reports/graph/*.svg` |
| Captions | `reports/graph/captions.md` |
| This file | `docs/graph/prereg.md` |

---

## 12. Limitations to state in results

- Swipe decisions are conditioned on feed exposure (G1); we observe only swiped profiles.
- Results (b) and (c) are described as "behaviour conditional on exposure" until feed
  mechanism is clarified by the data provider.
- Match ≠ flat rental; swipe ≠ interest in renting.
- Right swipe / match is an in-app signal, not a real-world outcome.
