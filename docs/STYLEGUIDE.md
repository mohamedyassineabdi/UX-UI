# Engineering Styleguide

**Status:** Observed current conventions, not a new formatter policy
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b` (the application implementation baseline; current documentation integration is `bfb3c95`)
**Last updated:** 2026-09-11
**Audience:** Contributors and reviewers
**Scope:** Conventions evidenced by the repository; no unconfigured lint/format/type rules are imposed.
**Related documents:** [Contributing](../CONTRIBUTING.md), [Testing](TESTING.md), [Security](SECURITY.md), [Architecture](ARCHITECTURE.md).

## General and Python

Prefer explicit validation, bounded execution, evidence preservation, and safe failure over inferred success. Python modules use `snake_case`, classes/dataclasses/Pydantic models in `PascalCase`, type annotations where they clarify contracts, `pathlib.Path` for repository paths, and narrow helpers for environment parsing. Keep external input validation at trust boundaries; retain error/event context without leaking credentials. Use atomic workspace writes and validated job/path identifiers rather than raw paths.

Tests are `tests/test_*.py`, describe observable behavior, and use fixtures/temporary files rather than generated repository outputs. Add a focused regression test for a changed contract; do not claim a formatter, linter, or type checker is mandatory because none is configured.

## Frontend, API, and persistence

React source lives in `src/ui/frontend/`: components use `PascalCase`, hooks start `use`, and API calls are centralized in `api/`. Do not hand-edit `src/ui/static/app/`; Vite generates it. Preserve bearer-header handling and the API client's JSON/error/request-ID behavior.

Routes use explicit method/path branching, JSON error envelopes, owner-scoped `404`s, and admin checks for criteria mutation. Database schema changes belong in ordered `JobStore` migrations with a schema-version increment, indexes appropriate to query paths, and explicit foreign-key behavior. Use `BEGIN IMMEDIATE` for state changes needing single-host serialization; revisions/events are append-only and publication snapshots immutable.

## Security-sensitive work and documentation

Validate public URLs, redirects, browser destinations, uploads, paths, subprocess inputs, and environment values before use. Do not weaken the default-deny interaction policy, auth fail-closed behavior, or deployment-mode guard without tests and an ADR where architectural.

Documentation uses a metadata header, relative links, factual status labels, concise tables, and Mermaid only where it clarifies a relationship. Use the project vocabulary: website, screenshot, Figma, Android/mobile, job, audit, finding, evidence, measurement, review, and publication. Never add credentials, generated artifacts, virtual environments, or build output to commits.
