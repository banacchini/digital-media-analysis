# AI-use disclosure

Copy to `docs/ai-disclosure.md` and keep current. Feeds the AI-use statement in the preprint.

| Date       | Person           | Tool / model            | Purpose                             | Output used? (how, after what verification)                                                                                                                                                                                                                                                                                                  | Log path                                                                     |
| ---------- | ---------------- | ----------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 2026-10-18 | Jakub Smolarczyk | Gemini 3.8 Flash medium | Code generation ; hypothesis advice | Adopted in src/rentfriends/EDA.py, running ruff and checking that generated figures match actual metadata of the dataset, also adapted and executed in notebooks/EDA.ipynb, verified against dataset outputs. ; used to formulate notes in notebooks/EDA.ipynb after double-checking rules in docs/rentfriends_hipotezy_karta_eksploracji.md | `logs/ai/gemini/maxster256/2026-10-18-hypotheses-feasibility-eda-code.jsonl` |
|            |

## Statement for the report (draft)

Describe which parts of data processing, analysis, code and text involved AI, which outputs were
verified by whom, and what was not verified (e.g. literature suggestions).

## Instruments

AI models used as measurement instruments in the analysis: model, version, prompt, validation reference (codebook).
