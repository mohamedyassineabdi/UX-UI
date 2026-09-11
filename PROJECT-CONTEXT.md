# Project Context

**Status:** Compact current orientation
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** AI/code agents, maintainers, and reviewers
**Scope:** Fast orientation; detailed contracts remain in the linked documents.
**Related documents:** [README](README.md), [Technical Specification](docs/TECHNICAL-SPECIFICATION.md), [Architecture](docs/ARCHITECTURE.md), [Checkpoint](docs/CHECKPOINT.md).

UX/UI Auditor creates evidence-backed UX/UI audit reports from public websites, uploaded screenshots, Figma files, and Android/mobile applications. It is not a full-site crawler, WCAG certification, or field-performance product.

## Current model

The implemented path is React/Vite frontend -> Python HTTP server/API -> SQLite job store and local workers -> mode-specific pipelines -> evidence/measurement -> evidence-aware scoring -> machine report -> optional structured review -> immutable publication snapshot. It is one application instance, not a microservice or distributed system.

Website audits use bounded representative sampling. Findings retain outcome, applicability, measurement state, stable identifiers, and provenance. Collection coverage differs from measurement coverage. The five axes are **Performance & Task Execution**, **Flow & Architecture**, **Trust & Accessibility**, **Visual & UI Consistency**, and **Content & Microcopy**. SQLite schema version 3 stores jobs/events, review revisions/events, and publication snapshots.

Bearer authentication and owner-scoped access protect audit, report, artifact, review, and publication records. URL/network safeguards and conservative interaction rules limit audit behavior. The Python server serves the React/Vite production build.

## Constraints and unresolved decisions

Render currently disables screenshot and live-mobile execution; verify deployment/configuration before treating this as product policy. Local SQLite/artifacts require external durable storage on ephemeral deployment and do not support safe multi-instance coordination. Score calibration/KPI approval, hosted screenshot/mobile scope, and any distributed deployment requirement remain unresolved. Accessibility recommendations are not compliance evidence; operational records are not dedicated product analytics; model output remains probabilistic.

Phases 1-4 documentation are completed. Phase 5 provides agent operating guidance. Start with [Reading Map](READING-MAP.md), then use [Checkpoint](docs/CHECKPOINT.md) for current handoff facts.
