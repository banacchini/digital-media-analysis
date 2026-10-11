# AGENTS.md

Instructions for AI coding agents (and humans) working in this repository.
`CLAUDE.md` and `GEMINI.md` are symlinks to this file; edit only `AGENTS.md`.

## Project

University course project (Analiza Mediów Cyfrowych / AMC): an empirical study of which
parameters influence the decision to rent a flat together, based on anonymised data from
RentFriends, a Tinder-like roommate-matching app.

- Project knowledge base (research question, data, risks, provenance log): `docs/RENTFRIENDS.md`
- Course rules and grading: `docs/AMC-1.md`
- The research question is still being narrowed to one testable thesis. Do not assume a final hypothesis.

## Principles from the course

- Goal is a **verified conclusion whose scope and confidence match the evidence**, not a model score (no F1 chasing).
- A well-justified **negative result** is a full result. Use a shuffled/null baseline.
- Unit of analysis is the user pair (A, B); the same user appears in many pairs, so use user-level splits or user-clustered standard errors.
- Distinguish correlation from causation; report uncertainty and robustness checks; state limitations.
- Any AI-based instrument (e.g. LLM labelling of bios) must be validated against a human gold standard (codebook first).

## Setup and commands

```bash
uv sync                      # install deps (Python 3.13)
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv run pre-commit install    # once per clone
```

## Layout

- `src/rentfriends/` analysis code; `tests/` tests; `notebooks/` exploration (strip outputs before commit)
- `data/{raw,interim,processed}/` **never committed** (only `.gitkeep`)
- `docs/` project docs; `docs/templates/` templates for M1 card, codebook, data statement, AI disclosure
- `reports/{preprint,poster}/` deliverables
- `logs/ai/<tool>/<author>/` exported AI-agent session logs (see `logs/ai/README.md`)

## Hard rules

1. **No data in git or in prompts.** Never commit anything under `data/` and never paste raw rows or bios into a chat unless unavoidable; bios may contain personal data (names, phones, social links). Follow `data/README.md`.
2. **No invented sources.** Literature listed in `docs/RENTFRIENDS.md` is unverified. Verify every citation in the source before use; never fabricate references, numbers or results.
3. **Log AI sessions.** Every substantive session with an AI tool is exported to `logs/ai/` by the person who ran it and committed (instructions: `logs/ai/README.md`). The course grader reads these logs.
4. **Disclose AI use.** Keep `docs/ai-disclosure.md` (from the template) up to date; it feeds the report's AI-use statement.
5. **Record provenance.** When using a web source or tool output in the project, add it to section 9 of `docs/RENTFRIENDS.md`.
6. **Individual contribution matters.** Commit your own work under your own identity, in small commits with clear messages. Do not commit on behalf of a teammate. Agents: do not commit or push unless the user asks.
7. **Legality first.** No scraping of third-party platforms; see `docs/RENTFRIENDS.md` section 5.

## Conventions

- Python 3.13, `ruff` for lint and format, type hints on public functions.
- Reproducibility: fix random seeds, keep analysis in scripts/modules rather than only in notebooks.
- Commit messages: imperative, short subject (`Add pair-level feature builder`).
- Write docs and code comments in English.
