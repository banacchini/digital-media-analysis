# data/

Local-only. Everything here except `.gitkeep` and this file is gitignored and blocked by pre-commit.

- `raw/` files exactly as received from RentFriends (never edit)
- `interim/` cleaned or joined intermediate tables
- `processed/` analysis-ready tables

Rules:

- Do not commit, upload, or paste into AI chats raw rows or bio text. Bios may contain names, phone numbers or social links (audit pending, see `docs/RENTFRIENDS.md` section 4).
- Document origin, collection, anonymisation, known gaps and permitted use in `docs/data-statement.md`.
- Confirm that user identifiers are consistent across profile and action tables before any pair-level analysis.
- Derived artefacts for the report should be aggregated; do not publish row-level data.
