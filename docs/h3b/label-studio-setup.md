# Label Studio: setup and annotation protocol (H3b-ii gold set)

Each of the three annotators (A, B, C) labels 50 bios, each bio is labelled by exactly two people
(`docs/h3b/gold-sampling.md`). Four binary signals per bio: `towarzyskie`, `spokoj`, `rytm`,
`intencja` (1 = present, 0 = absent), plus optional free-text `uwagi`.

`label-studio/labeling_config.xml` was written from the Label Studio configuration syntax but not
tested in a running instance. After pasting it, check the preview (step 3) before sharing.

## Privacy rules

- Bios may contain personal data. Run Label Studio **locally on your own machine**, with its data
  directory outside this repository. Do not use a hosted or shared server.
- Each annotator gets only their own `annotator_X.labelstudio.json` (from `data/private/gold/`),
  sent privately. Never commit it, paste it into a chat or an AI tool.
- Do not open the other annotators' files or exports.

## Setup (per annotator)

1. Install in a separate virtual environment (not the project's):
   ```bash
   python -m venv ~/ls-venv && source ~/ls-venv/bin/activate
   pip install label-studio
   label-studio start
   ```
   Open the URL it prints (default http://localhost:8080) and create a local account.
2. **Create project** named `gold-X` (your letter). Skip the data import for now.
3. *Settings > Labeling Interface > Code*: paste `label-studio/labeling_config.xml`, save. The
   preview should show the bio text, four 1/0 radio groups and a notes box.
4. *Settings > Annotation*: set task sampling to sequential, so you see tasks in the imported
   order (that order is already your private random order). Enable "Show only your own
   annotations" if offered.
5. *Data Manager > Import*: upload your `annotator_X.labelstudio.json` (JSON list of tasks with
   `item_id` and `text`). You should see 50 tasks.

## Annotating

1. Read the codebook with the signal definitions first (`docs/h3b/codebook.md`, still to be
   written; do not start before it exists).
2. Label independently. Do not discuss items with the other annotators until all three have
   finished. Questions about definitions go to the codebook author, without quoting bios.
3. Click *Label All Tasks*. For each bio answer all four signals (each is required), then Submit.
   Use `uwagi` for doubts. Do not edit submitted annotations later.
4. Take each bio as written; label what the text says, not what you would infer.

## Export and import

1. *Data Manager > Export > JSON* (the full format, not JSON-MIN or CSV). Save as `export_X.json`
   outside the repo, or in `data/private/gold/`.
2. Once all three exports are collected in one place:
   ```bash
   uv run python scripts/gold_import.py \
     --input A=export_A.json --input B=export_B.json --input C=export_C.json
   ```
   It writes `data/private/gold/labels_long.parquet` (`item_id`, `annotator`, `signal`, `value`)
   and prints only integers: items, annotations, validation errors. Expected: 75 items, 600
   annotations (50 x 3 annotators x 4 signals), 0 errors. On errors it writes nothing and prints
   the error counts by type (`missing`, `unexpected`, `duplicates`, `bad_values`).
3. The filled CSVs (`annotator_X.csv`, columns `towarzyskie` ... `intencja` with 0/1) are accepted
   too, as `--input A=annotator_A.csv`.
