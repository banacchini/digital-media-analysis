# AI-use disclosure

Copy to `docs/ai-disclosure.md` and keep current. Feeds the AI-use statement in the preprint.

| Date       | Person           | Tool / model            | Purpose                             | Output used? (how, after what verification)                                                                                                                                                                                                                                                                                                  | Log path                                                                     |
| ---------- | ---------------- | ----------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 2026-10-18 | Jakub Smolarczyk | Gemini 3.8 Flash medium | Code generation ; hypothesis advice | Adopted in src/rentfriends/EDA.py, running ruff and checking that generated figures match actual metadata of the dataset, also adapted and executed in notebooks/EDA.ipynb, verified against dataset outputs. ; used to formulate notes in notebooks/EDA.ipynb after double-checking rules in docs/rentfriends_hipotezy_karta_eksploracji.md | `logs/ai/gemini/maxster256/2026-10-18-hypotheses-feasibility-eda-code.jsonl` |
| 2026-10-19 | Dominik (banacchini) | Claude Code (Claude Sonnet 5.5) | Documentation: filling in missing data in the exploration card | Numbers, distributions and feasibility notes from notebooks/EDA-rendered.ipynb transcribed into docs/rentfriends_hipotezy_karta_eksploracji.md (sections 2, 3.4, 4, 5). Used after review of the diff against the notebook outputs; the model only read the notebook text outputs, not the figures or the ERD image, and could not read data/processed. Derived values (e.g. same-sex acceptance, 9.4% of mutual-decision pairs ending in a match, 10x-rule limit of ~73 variables) and the proposed n_min = 10 threshold are the model's own calculations or proposals and need confirmation by the author. | `logs/ai/claude/<author>/2026-10-19-eda-card-fill.jsonl` (to be exported per `logs/ai/README.md`) |
|            |

## Statement for the report (draft)

Describe which parts of data processing, analysis, code and text involved AI, which outputs were
verified by whom, and what was not verified (e.g. literature suggestions).

## Instruments

AI models used as measurement instruments in the analysis: model, version, prompt, validation reference (codebook).
