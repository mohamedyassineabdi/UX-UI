# Engineering Checkpoint

**Status:** Current handoff
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** Next engineer, maintainer, product/UX handoff reader
**Scope:** Current remote implementation baseline and documentation integration state.
**Related documents:** [Roadmap](ROADMAP.md), [Implementation Plan](IMPLEMENTATION-PLAN.md), [Security Operations](SECURITY_OPERATIONS.md).

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

This checkpoint is being reconciled in a clean integration worktree from remote baseline `b49d8ac`. Local documentation commits `7245553` and `83c3fd0` were required; README and Architecture were manually reconciled against remote frontend/review changes. Do not use the original dirty worktree as a source for application behavior.

## Verification

Relevant current-baseline tests to run/retain: `tests/test_phase2b_semantics.py`, `tests/test_phase3a_scoring.py`, `tests/test_phase3b_measurement.py`, `tests/test_review_workflow.py`, `tests/test_review_ui_contract.py`, `tests/test_axe_runner.py`, and `tests/test_lighthouse_runner.py`, plus `npm run build`. Documentation validation must include links, anchors, metadata, traceability and `git diff --check`.
