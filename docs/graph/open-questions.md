# Open Questions — Graph Analysis

Recorded per the prompt specification. Each item notes the **conservative choice** taken.

| ID | Question | Conservative choice | Note |
|---|---|---|---|
| OQ1 | Does the h1_analysis_dataset include all Hyderabad-filtered swipes, or just complete-case rows? | Use h1 as universe (94 295) = already filtered; document difference from 93 717 | Logged in `data-contract.md` |
| OQ2 | Is "pairs with both swipes" = unordered {A,B} pairs where both A→B and B→A are in h1? | Yes, 7 790 ordered swipe-pairs → 7 790 / 2 unordered pairs | Empirically 15 544 directed swipes / 2 = 7 772 unordered pairs; small discrepancy vs 7 790 in prompt may be from h1 vs raw swipes |
| OQ3 | Should match_col from h1 be used? | No — leakage risk. Reconstruct match as `y_right_A AND y_right_B` from pair edges only | Consistent with hard rule in prereg |
| OQ4 | The prompt mentions 487 matches in 7 790 pairs; h1 shows 1 218 `match==1`. | Use pair-level reconstruction (y_right_A AND y_right_B) for analysis (b) universe | 1 218 includes one-sided swipes where the other side was recorded differently |
| OQ5 | PyG availability for M3/M4 on MPS? | Implement GraphSAGE manually in pure PyTorch if PyG install fails | Try PyG first; fall back to custom SAGE |
| OQ6 | Early stopping patience of 20 at max 300 epochs on MPS may be slow for M3/M4 with large batch. | Use full-batch training on CPU for LightGCN; MPS for GNN with features if faster | Log device used in `numbers.json` |
| OQ7 | Day ordering unavailable for Z9 (learning curve). | Disclose in Z9 output that order is unknown; use random reveal | Per prompt specification |
| OQ8 | city_diff column not in h1 (checked empirically). | Compute at feature-build time from city_sender ≠ city_receiver | Stored as binary indicator |
| OQ9 | 2-hour training cap per user request. | Reduce max epochs to 100 and hyperparameter grid to ≤ 6 configs for M2–M4 | Documented in prereg post-hoc addendum |
