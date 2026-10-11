# AI session logs

The course grades individual work partly from logs of sessions with AI agents (Claude, Codex,
Gemini, others). Export them here manually.

## Layout

```
logs/ai/<tool>/<handle>/YYYY-MM-DD-<short-topic>.<md|jsonl>
```

`<tool>` is one of `claude`, `codex`, `gemini`, `other` (put the product name in the filename for `other`).
`<handle>` is your GitHub handle. Create your folder on first export.

## How to export

| Tool | Where the raw session lives | Export |
|---|---|---|
| Claude Code | `~/.claude/projects/<project-path>/*.jsonl` | copy the relevant `.jsonl` (or use `/export` for a text transcript) |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` | copy the relevant `.jsonl` |
| Gemini CLI | `~/.gemini/tmp/<hash>/chats/` or `/chat save <tag>` | copy the saved chat file |
| Web chats (ChatGPT, Claude.ai, Gemini, ...) | in the web UI | use the platform export or paste the full conversation into a `.md` file |

Paths can change between tool versions; if a path is wrong, export in whatever way preserves the
full conversation including tool calls, and say how in the PR.

## Rules

- Export **complete** sessions; do not cherry-pick or edit content.
- Before committing, check for secrets (tokens, keys, `.env` contents) and for raw data or personal data from RentFriends. Redact with `[REDACTED]` and nothing else; mention the redaction in the commit message.
- Commit logs with the work they relate to, or at the latest at the end of the week.
- Sessions without a native export (IDE chats etc.): save a faithful copy as `.md` and list it in the PR.
