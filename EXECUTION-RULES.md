# Execution Rules

**Status:** Recommended safe operating workflow
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** AI/code agents and contributors
**Scope:** Inspection, implementation, validation, documentation, and integration workflow.
**Related documents:** [AI Instructions](AI-INSTRUCTIONS.md), [Reading Map](READING-MAP.md), [Testing](docs/TESTING.md), [Quality Gates](docs/QUALITY-GATES.md).

## Establish and protect state

Run `git fetch origin --prune`, `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, and `git rev-parse origin/main`. Never assume local `main` is current. If the worktree is dirty, do not reset, clean, stash, rebase, or overwrite it without explicit intent; prefer `git worktree add -b <branch> <path> origin/main`.

## Work narrowly

Use [Reading Map](READING-MAP.md), inspect actual source/config/tests/history, define affected scope/docs/tests/security implications, and implement only the requested change. A docs-only task permits no source, test, package, Docker, CI, schema, or runtime edits. Do not use documentation alone as proof of implementation.

## Validate and synchronize documentation

Use [Testing](docs/TESTING.md) and [Quality Gates](docs/QUALITY-GATES.md). Current baseline commands are `npm ci --ignore-scripts`, `npm run build`, `uv sync --frozen`, `uv run python -m compileall src figma_audit navigator scripts`, and `uv run pytest -q`; run focused tests for changed behavior. Record environment aborts as **NOT VERIFIED**, not passed. Map changes to docs: API -> API spec; DB -> Database spec/Data Model; UX -> UX/design/content/accessibility; config -> Configuration; security -> Security/Operations; deployment -> Deployment/Release; architecture -> Architecture/ADR; project state -> Checkpoint/Roadmap/Milestones.

## Review, stage, and integrate

Inspect `git status --short`, `git diff --check`, `git diff --stat`, and `git diff`; verify intended files only. Stage explicit paths, avoid `git add .` for mixed scope, and use focused commits. Fetch again before push; if `origin/main` advanced, inspect/reconcile/revalidate. Prefer a PR where available; never force-push, bypass branch protection, or claim external systems (Docker, auth, Figma, Appium, Vercel, model providers, target sites) succeeded without verification. Confirm remote `main` contains integrated work and update [Checkpoint](docs/CHECKPOINT.md) when project state materially changes.

## High-risk operations and temporary tooling

`git reset --hard`, `git clean`, rebase, `git filter-repo`, and force push require explicit authorization, a justified scope, and verified targets; credential-history work also requires the coordination described in [Security Operations](docs/SECURITY_OPERATIONS.md). Temporary validation scripts/databases must not be committed unless intentionally made project artifacts.
