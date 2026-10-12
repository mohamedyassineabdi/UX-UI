# UX-UI auditor — how we work in this repo

Loaded automatically by Claude Code. Keep it short; details live in `docs/`.

## Workflow (superpowers plugin)
- New feature or behaviour change → `superpowers:brainstorming` first: classify spike / bounded / architectural, ask one question at a time, get approval.
- Architectural work → spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, then `superpowers:writing-plans` → plan in `docs/superpowers/plans/`. Plans are lean: exact files, interfaces and test assertions, no full code listings.
- Execute plans with `superpowers:executing-plans` (inline, "Native"): TDD per task (watch the test fail, then pass), one commit per task, a ledger of rulings, then ONE independent whole-branch review by a fresh subagent on the most capable model before finishing.
- Bugs → `superpowers:systematic-debugging`; never fix without a failing test first.
- Charts → `dataviz` skill; run its palette validator, don't eyeball colours. UI work → check real rendering with Playwright screenshots before calling it done.

## Project rules
- Product copy never says "Claude", "VLM" or "machine finding" to clients — say "the AI agent". Raw enums and IDs only in report appendices.
- Client-facing output must look like a Big 4 / EY Studio+ deliverable: no raw JSON on screen anywhere (use `ReadableRecord`), clear hierarchy, labelled values.
- The client report (`src/report/client/`) is the single source for the in-app Client report tab, the deployed snapshot and the PDF. Change it there, never in three places.
- Untrusted text is always escaped; the client report HTML stays script-free and self-contained.
- Commit only files you changed; other sessions may have uncommitted work in the tree.

## Commands
- Python: `.venv/Scripts/python.exe` (3.12). Tests: `.venv/Scripts/python.exe -m pytest -q` (browser tests need `npm run build` first; full suite ≈ 3 min).
- Frontend: `npm run build` (Vite → `src/ui/static/app/`). Server: `npm run ui`.
- Local `.env` (git-ignored) is required — see `docs/HANDOFF-2026-10-06.md`.

## Token discipline
Short sessions, one task each; lean plans; subagents only for broad searches or an independent review of risky code. Long test runs go to a file / background, read the tail.
