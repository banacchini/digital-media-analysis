# Codebook

Owner: pipeline engineer. Template: `docs/templates/codebook.md`.

Defines (A) the raw profile fields, (B) the tag variables labelled by a human
gold standard, (C) every derived model variable, and (D) the validation of the AI instrument.
Decisions are referenced as D1-D22 (`docs/prompts/m1-generation-plan.md`) and limitations as G1-G18
(`docs/rentfriends_hipotezy_karta_eksploracji.md`). Hypotheses follow the M1 card: H1 lifestyle vs
age/interests, H2 demographics (effect size), H3a bio effort.

## Part A. Raw field dictionary

Source: `users` / `profile_history`. All columns are nullable (data statement). Fill one row per
field from the local database (distinct values and share missing only, no user rows).

| Field | Type | Role | Values (code → meaning) | % missing | Ordered? |
|---|---|---|---|---|---|
| `sex` | 1 char | H2 | F, M, O (O = own level, D8; 65 of 101 changes lead to O, meaning unclear) | | no |
| `age_band` | text | H2 | 18-20, 21-23, 24-26, 27-30, 31-35, 36+; 27+ merged in analysis (D9) | | yes |
| `city` | text | control | e.g. Wrocław, Warszawa, "inne" (privacy generalisation), Hyderabad (excluded) | | no |
| `daily_routine` | text | H1 lifestyle |  | 74-81% (card) |  |
| `lifestyle` | text | H1 lifestyle | | 74-81% (card) | |
| `work_from_home` | text | H1 lifestyle || 74-81% (card) | |
| `cleanliness` | text | H1 lifestyle | VT, FT, R, NULL| 1.0% | |
| `noise_level` | text | H1 lifestyle | Q, P, R, M, NULL | 1.2% | |
| `smoking` | text | H1 lifestyle | Y, N, V, O, NULL | 79.3% | |
| `alcohol` | text | H1 lifestyle | BM, NE, SO, SN, ND, NULL | 74-81% (card) | |
| `interests` | jsonb list | H1 (see Part B) | tags, max 9 per user, two formats (emoji label and snake_case slug) | 2.57% empty | no |
| `bio`, `bio_length` | text, int | H3a | free text; `bio_length` disagrees with text length for ~2.3% of profiles (G18) | 46.6% empty (card: 53.4% have bio) | |
| `room_type`, `search_goal`, `budget` | | not in H1-H3 | | | |

Rules:
- Fields whose codes are unordered or unknown are compared by **equality only**, with no direction
  (D14). A field may be marked ordered only after the team agrees on the order.
- Whether a lifestyle field is a user's own trait or a preference about a flatmate is unknown
  until the provider answers. Working assumption: **own trait**. Limitation to state in the report.

## Part B. Tag variables (AI instrument + human gold standard)

Source: `users.interests` and `profile_history.interests`. Tags are lifestyle, status or hobby
without distinction in the raw data, so the interests block of H1 would otherwise partly measure
lifestyle (M1 card, Fig. 1).

### B.1 Variable `canonical_tag`

- Definition: the single canonical snake_case slug for a raw tag string.
- Unit: tag string (124 raw strings, 54 of them emoji forms).
- Rule: strings that name the same app option in both formats map to one slug. Where a string
  cannot be assigned with confidence, it keeps its own slug and is marked `unclear_mapping`.
- After mapping, duplicates within one user are removed (A3); report the effective tag count.
- Source field: `interests`.
- Coded by: AI instrument proposes the map, human reviews and corrects. Metric: share of mappings
  changed by humans, plus the list of changes.

### B.2 Variable `tag_category`

- Definition: what a canonical tag describes.
- Unit: canonical tag.
- Values and decision rules (fixed by D12; examples are from the card, borderline cases to be
  completed after annotation):

| Value | Rule | Examples |
|---|---|---|
| `lifestyle` | Habit or living preference that affects sharing a flat: smoking, noise, cleanliness, daily rhythm, pets, social energy | `non_smoker`, `quiet_after_22`, `night_owl`, `likes_pets`, `extrovert`/`introvert` (D12) |
| `status` | Social or occupational status, not a habit | `student` (D12) |
| `hobby` | Activity or interest with no direct effect on sharing a flat | `cooking`, `movies_cinema` |
| `unclear` | Annotator cannot choose between the above from the tag name alone | |

- Annotators see the canonical tag name only, not user profiles.
- Coded by: AI instrument (model, version and prompt file to be recorded in B.5) and human gold
  standard; the final value is the human adjudicated label.

### B.3 Variable `linked_field`

- Definition: the structured field that describes the same trait as a lifestyle tag, or `none`.
- Examples from the card: `non_smoker` / `smoker` / `vapes` ↔ `smoking`; `quiet_after_22` /
  `quiet_evenings` ↔ `noise_level`; `loves_cleanliness` ↔ `cleanliness`.
- Rule (D13): when tag and field describe the same trait, the **field takes priority and the tag
  fills the gap** when the field is missing. Agreement between the two is reported.

## Part C. Derived model variables

Every model column has one row here. Computed per swipe A→B with the as-of rule from section 0.
"Block" is the unit compared in H1 (1-3 scalars per block, D16). One main definition per block,
fixed before modelling (G8).

| Variable | Block | Definition | Source | Missing handling | Used in |
|---|---|---|---|---|---|
| `y_right` | outcome | 1 if A swiped right on B's profile, else 0 | `swipes.direction` | n/a | main outcome (D4) |
| `match` | outcome | 1 if both swiped right; only pairs with both swipes recorded | `swipes` | the 246 matches with one swipe are out of the model | secondary (D5) |
| `sex_pair` | demographics | sender sex × receiver sex, O as own level | `sex` | | H2 |
| `same_sex` | demographics | 1 if sender sex = receiver sex | `sex` | | H2 |
| `age_band_diff` | demographics | signed difference of band index (receiver − sender), 27+ merged | `age_band` | | H2, H1 baseline |
| `same_band` | demographics | 1 if same band after merging | `age_band` | | H2, H1 baseline |
| `lifestyle_field_agree_k` | lifestyle | for field k of the 7: agree / differ / either missing | Part A fields | "missing" level | H1 |
| `lifestyle_tag_conflict` | lifestyle | 1 if the pair has conflicting tags in a `polarity_group` (directional) | B.4 | 0 where one side lacks the group; field priority per D13 | H1 |
| `lifestyle_shared_n` | lifestyle | count of shared `lifestyle` canonical tags | B.2 | | H1 |
| `hobby_jaccard` | interests | Jaccard of `hobby` canonical tags after dedup | B.1, B.2 | 0 if both empty `[INPUT NEEDED: confirm]` | H1 |
| `tag_count_diff` | interests | effective tag counts of both sides (controls the Jaccard ceiling effect, cap 9) | B.1 | | H1, H3a |
| `bio_empty` | bio | 1 if receiver's bio is empty | `bio` | | H3a |
| `bio_len` | bio | receiver's bio length in characters **counted from the text**, not `bio_length` (G18) | `bio` | | H3a |
| `profile_completeness` | control | share of the 7 lifestyle fields that are non-missing, receiver | Part A | | H3a |
| `same_city` | control | same / different / unknown (for "inne") | `city` | 3 levels | all |

Random effects (not columns): sender and receiver intercepts for generosity and popularity (A2).

## Part D. Gold standard and instrument validation

### D.1 Gold standard

- Sample: all canonical tags (69 - see interests_mapping), no sampling.
- Annotators: Dominik Czech, Michał Jankowski, Jakub Smolarczyk.
- Procedure: each annotator labels `tag_category` independently, from this codebook, **blind to the
  agent's proposals** and to each other. Disagreements are adjudicated together; the adjudicated
  label is final.
- Inter-annotator agreement: metric Cohen's κ per pair (Fleiss' κ for three), value and 90% CI. Reported as the ceiling for the agent.

### D.2 Instrument validation

- Compared against: adjudicated gold standard. Metrics: Cohen's κ agent vs gold with 90% Confidence Interval (CI), percent agreement, confusion matrix.
- Error analysis: systematic failure modes (emoji forms, `unclear`, tags near the
  lifestyle/hobby boundary); subgroup split by raw format.
- Caveat: with a small number of tags the κ CI is wide; report it as such.


## Provenance

- Decisions D1-D22 come from the team and `docs/prompts/m1-generation-plan.md`. Counts are from
  the M1 card (before the Hyderabad filter and profile versioning).
- This draft was written with Claude Code (see `docs/ai-disclosure.md`) and reviewed by the team.
