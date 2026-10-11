# Contributing

Grading is individual: contribution is judged from commits, AI session logs, documentation
and oral defence (see `docs/AMC-1.md`, section 4.1). Commit count alone is not the measure.

## Roles (from the course)

| Role | Owner | Responsibility |
|---|---|---|
| Research lead | _TBD_ | question, hypotheses, coherence of conclusion |
| Data engineer | _TBD_ | data acquisition, GDPR/platform terms, data statement |
| Pipeline engineer | _TBD_ | codebook, gold standard, instrument validation, error analysis |
| Analyst | _TBD_ | robustness analyses, visualisation (in a 3-person team: shared by lead and pipeline engineer) |

Fill in owners (GitHub handles) when the team is fixed.

## Workflow

- Branch from `main`: `<handle>/<topic>`; open a PR using the template; at least one teammate reviews.
- Small, focused commits under your own identity. Never commit data (`data/`) or secrets.
- Run `uv run ruff check . && uv run pytest` before pushing; pre-commit enforces the basics.
- After each AI session, export the log to `logs/ai/<tool>/<handle>/` (see `logs/ai/README.md`) and commit it with the related work.
- Note AI assistance in the PR description and in `docs/ai-disclosure.md`.
