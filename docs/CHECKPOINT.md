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

## Documentation publication state

Current repository HEAD: `786eae64873373614ca2f6872d06f0358b4de43f`. Application implementation baseline: `b49d8ac0ca9b89da97629c734fa50d5245b5420b`. Phase 1 source-of-truth and Phase 2 engineering documentation are published on `origin/main`. The engineering layer provides API, database, security, testing, deployment, environment, configuration, style, and contribution guidance.

## Current validation (2026-09-11)

| Check | Result |
| --- | --- |
| Locked dependencies, frontend install/build, Python compilation | **PASSED** — `uv sync --frozen`; `npm ci --ignore-scripts`; `npm run build`; `uv run python -m compileall src figma_audit navigator scripts` |
| Documentation validation | **PASSED** — relative links, anchors, Mermaid blocks, metadata, traceability, secret-pattern scan, and `git diff --check` |
| Deterministic Python suite | **PASSED** — `112 passed` with `tests/test_auth_integration.py` excluded |
| Explicit security suite | **PASSED** — `53 passed` for auth, network policy, server, upload, frontend, and publication security |
| Feature regression suite | **PASSED** — `55 passed` for jobs, review/publication, semantics, scoring, measurement, Axe/Lighthouse, discovery/workspace, and frontend contract/security |
| Auth integration smoke test | **NOT VERIFIED** — local Windows OpenSSL abort (`OPENSSL_Uplink ... no OPENSSL_Applink`) prevented `tests/test_auth_integration.py` from recording a result |
| Docker image build | **NOT VERIFIED** — Docker daemon unavailable locally |
