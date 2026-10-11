# RentFriends: what drives the decision to share a flat?

Course project (Analiza Mediów Cyfrowych). We analyse anonymised swipe/match data from
RentFriends, a Tinder-like roommate-matching app, to test which profile-compatibility
parameters are associated with mutual matches.

Status: research question being narrowed. See [docs/RENTFRIENDS.md](docs/RENTFRIENDS.md).
Course rules: [docs/AMC-1.md](docs/AMC-1.md).

## Quick start

```bash
uv sync
uv run pre-commit install
uv run pytest
```

Requires [uv](https://docs.astral.sh/uv/). Python 3.13 is pinned in `.python-version`.

Data is **not** in the repo. Place the files received from RentFriends in `data/raw/`
(see [data/README.md](data/README.md)); never commit them.

## Structure

| Path | Purpose |
|---|---|
| `src/rentfriends/` | analysis code |
| `tests/` | tests |
| `notebooks/` | exploration |
| `data/` | local-only data (gitignored) |
| `docs/` | project docs and `templates/` (M1 card, codebook, data statement, AI disclosure) |
| `reports/` | preprint and poster |
| `logs/ai/` | exported AI-agent session logs (graded) |

## Working with AI agents

The agent layer follows the open [AGENTS.md](https://agents.md) standard. Everything lives in
[AGENTS.md](AGENTS.md); `CLAUDE.md` and `GEMINI.md` are symlinks to it.

- Codex, Cursor, Copilot, Aider (with `read: AGENTS.md`) and most others read `AGENTS.md` directly.
- Claude Code reads `CLAUDE.md`; Gemini CLI reads `GEMINI.md` (both symlinks, so no setup needed).
  On Windows, enable symlinks (`git config core.symlinks true`, developer mode) or tell the tool to use `AGENTS.md`.
- **Export your session logs** to `logs/ai/` after each session: [logs/ai/README.md](logs/ai/README.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) for roles and workflow.
