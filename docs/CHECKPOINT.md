# Engineering Checkpoint

**Status:** Current handoff
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Next engineer, maintainer, product/UX handoff reader
**Scope:** Current remote implementation baseline and documentation integration state.
**Related documents:** [Roadmap](ROADMAP.md), [Implementation Plan](IMPLEMENTATION-PLAN.md), [Testing](TESTING.md), [Security Operations](SECURITY_OPERATIONS.md).

## Current baseline

The application uses a React/Vite frontend built into `src/ui/static/app/` and served by the Python HTTP server. A single local SQLite-backed worker system executes website, screenshot, Figma, and Android/mobile jobs. Website workspaces now include evidence manifests plus Axe and Lighthouse paths.

Committed result semantics retain outcome, applicability, measurement state, stable IDs, and provenance. Measurement coverage is separate from page collection coverage. Evidence-aware five-axis scoring uses applicable measured pass/fail rules; Lighthouse results are laboratory data and visual-model output is probabilistic. SQLite schema version 3 stores jobs/events, append-only review revisions/events, and publication snapshots.

The review lifecycle is machine audit -> revision -> validation -> approval -> immutable publication snapshot. Editing, validation, approval, and publication are distinct; arbitrary edited HTML is not accepted for publication. Render disables screenshot/live-mobile execution but not Figma.

## Constraints and open decisions

- Single application instance: SQLite/local artifacts are not distributed infrastructure; ephemeral persistence requires external durable storage.
- The system is not a full crawler, WCAG certification, or field-performance product.
- Score calibration/KPI approval, hosted-mode scope, and any distributed deployment requirement remain unresolved.
- External credential remediation remains a release prerequisite; the legacy incident path is not in reachable repository history.

## Documentation integration status

The source-of-truth documentation is reconciled in the clean `docs/source-of-truth-integration` worktree against remote baseline `b49d8ac`. Local documentation commits `7245553` and `83c3fd0` were reconciled by `bec23c5`; do not use the original dirty worktree as a source for application behavior.

## Phase 2 engineering documentation

The engineering layer now provides implementation-facing API, database, security, testing, deployment, environment, configuration, style, and contribution guidance. It is linked from the README and traces the same committed implementation baseline; detailed route/schema/variable contracts are authoritative in their respective engineering documents.

Phase 2 validation: frontend install/build and Python compilation passed. The complete deterministic Python remainder passed (`112 passed`) after the full suite again stopped at `tests/test_auth_integration.py` because of the local Windows OpenSSL runtime abort; that integration test remains **NOT VERIFIED**, not passed. Explicit security tests passed (`53 passed`) and focused job/review/publication/semantics/scoring/measurement/frontend tests passed (`55 passed`). Docker remains **NOT VERIFIED** because the local Docker daemon is unavailable. The Phase 2 worktree used an external temporary virtualenv after OneDrive hardlink/cache errors prevented a worktree-local `uv sync`; the locked environment itself then installed successfully.

## Final validation (2026-09-10)

- **PASSED:** `uv sync --frozen`; `npm ci --ignore-scripts`; `npm run build`; and `uv run python -m compileall src figma_audit navigator scripts`.
- **PASSED:** deterministic Python suite: `112 passed` with `tests/test_auth_integration.py` excluded after the full-suite attempt reached that test and the local Windows OpenSSL runtime aborted (`OPENSSL_Uplink ... no OPENSSL_Applink`) before pytest could record a result.
- **PASSED:** explicit deterministic security suite: `53 passed` for auth, network policy, server, upload, frontend, and publication security tests.
- **PASSED:** feature regression suite: `55 passed` for result semantics, scoring, measurement, Axe, Lighthouse, review, job queue, discovery/workspace, publication, and frontend contract/security tests.
- **NOT VERIFIED:** `tests/test_auth_integration.py`; local Windows OpenSSL runtime abort prevents the loopback integration smoke test from completing. This is not recorded as passed or failed.
- **NOT VERIFIED:** Docker image build; Docker CLI is installed but the local Docker Desktop Linux daemon is unavailable.
- Documentation validation must continue to include links, anchors, Mermaid blocks, metadata, PRD/spec traceability, secret scanning, and `git diff --check` before publication.
