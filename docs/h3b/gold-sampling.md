# H3b-ii gold set: sampling procedure

Builds the 75-bio set for manual annotation (gold standard for validating signal extraction from
bios). The builder never displays bio text; it logs only integers and SHA-256 digests. Output
files live in `data/private/gold/` (git-ignored) and are never committed.

Code: `scripts/gold_split.py` (split), `scripts/gold_import.py` (labels back in).
Annotation setup: `docs/h3b/label-studio-setup.md`.

## Parameters

- Random seed: **20261108** (`numpy.random.default_rng`; assignment and per-annotator orders use
  derived streams `[seed, 1]` and `[seed, 2, k]`).
- Sample: 75 = 45 uniform random + 30 enriched (quotas 8 / 8 / 7 / 7).
- Lexicons: `LEXICONS` in `scripts/gold_split.py`, frozen, not tuned on data. `docs/h3b/codebook.md` did not exist when they
  were frozen, so they derive from the task seeds plus inflections and English equivalents. They
  only enrich the sample; they do not define the signals.

## Procedure

1. **Candidates.** Non-empty bios (after `strip` and whitespace normalisation) from `users`
   (current profile, treated as newest) and `profile_history` (ordered by day, version).
2. **Hyderabad (D10).** Drop every account with city Hyderabad in any version.
3. **One text per user.** Latest non-empty version.
4. **Deduplication** of identical normalised texts across users (smallest `user_key` kept).
5. **G12 screen.** Drop texts matching: `phone` (9+ digits, optional separators), `email`, `url`
   (`http(s)://`, `www.`), `domain` (name + common TLD), `handle` (`@name`), `social`
   (messenger/social keyword + username), `long_digits` (6+ digits). Counts are per type, a text can
   match several. It is a conservative screen, not an audit (G12 stays open).
6. If the frame has fewer than 75 texts the build **stops** after printing the counts; filters are
   not relaxed.
7. **Random part first:** 45 drawn uniformly, independent of text.
8. **Enriched part:** from the remainder, sequentially for towarzyskie (8), spokoj (8), rytm (7),
   intencja (7): draw among texts matching the signal's lexicon, without replacement, excluding
   already selected texts (a text matching several lexicons goes to the first signal in that
   order). Any shortfall is filled uniformly at random from the remainder, keeps the short
   signal's stratum and is flagged `is_fill` in the master table.
9. **Assignment.** Items are split into 3 sets of 25 by one global round-robin across strata
   (random, then the four enriched, each shuffled), so each set has 15 random + 10 enriched and
   per-signal counts differ by at most 1. Set 1 -> A,B; set 2 -> A,C; set 3 -> B,C. Each annotator
   gets 50 items, each item has exactly 2 annotators, each annotator gets an independent random
   order. `item_id` (`g001`..`g075`) is assigned after a random shuffle and is unrelated to
   `user_key`. Annotators do not see the stratum.

## Outputs (`data/private/gold/`, not in git)

`gold_master.parquet` (`item_id`, `user_key`, `text`, `stratum`, `set_id`, `annotators`, plus
`is_fill`), `annotator_{A,B,C}.csv` (UTF-8, columns `item_id`, `text`, `towarzyskie`, `spokoj`,
`rytm`, `intencja`, `uwagi`), `annotator_{A,B,C}.labelstudio.json`.

## Run

```bash
uv run python scripts/gold_split.py
```

Prints integers and digests only; on an unexpected error only the exception type name.

## Results (filled in after the run)

Run of 2026-11-08, seed 20261108. All numbers are counts of users/texts.

| Step | Count |
|---|---|
| Users in `users` or `profile_history` | 2065 |
| Users with a non-empty bio (any version) | 1142 |
| Hyderabad accounts (any version) | 45 |
| Users with a bio after the Hyderabad filter (= one latest text each) | 1121 |
| Duplicate texts removed across users | 26 |
| G12 exclusions: phone / email / url / domain / handle / social / long_digits | 0 / 0 / 0 / 0 / 0 / 0 / 0 |
| G12 exclusions, total | 0 |
| **Candidate frame** | **1095** |

Zero G12 hits is lower than the earlier regex audit suggested (one version with `@` or a link).
That hit may lie in a Hyderabad account, a duplicate or a non-latest version; not checked, to
avoid inspecting content. Zero hits does not show the bios are free of personal data (names,
handles without `@`), so the annotation environment should be treated as private.

| Stratum | n | Shortfall filled at random |
|---|---|---|
| random | 45 | n/a |
| enriched_towarzyskie | 8 | 0 |
| enriched_spokoj | 8 | 0 |
| enriched_rytm | 7 | 0 |
| enriched_intencja | 7 | 0 |

Sets: 25 / 25 / 25 (set 1 = A+B, set 2 = A+C, set 3 = B+C). Items per annotator: A 50, B 50, C 50.

SHA-256 digests (of the sorted newline-joined lists, not the lists):

- `item_id` list: `bee618a18251bac8e677ffee0c90161c714a9119c03c665893b3320f354394e3`
- `user_key` list: `56c86f677468301072491fa26100c685dd340e75524bf6507bc389839ccd0e07`
- sorted `user_key|stratum` pairs: `faab88bfc8022d7652ab63da3561678a1ffafc312d63bdc8666540f24b6c1341`
- lexicons (canonical JSON): `cfd7f0831fffa50cbd88fadb78c738a2f28a0d6aaf753632db11460b038e9c17`

The `item_id` list is the fixed sequence g001..g075 by construction, so its digest only
fingerprints the format. Re-running with the same seed and data reproduces the other digests.
