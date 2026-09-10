# Engineering Decisions

**Status:** Evidence-backed ADR register
**Repository baseline:** `main @ 5d9646c4daa221f43c82cd8d477144900193bdb0`
**Last updated:** 2026-09-10
**Audience:** Developers, operators, and technical stakeholders
**Scope:** Architectural decisions, not product approval records.
**Related documents:** [Architecture](ARCHITECTURE.md), [Technical Specification](TECHNICAL-SPECIFICATION.md), [Implementation Plan](IMPLEMENTATION-PLAN.md).

Decision status is independent from rationale provenance. Status: Proposed, In progress, Implemented / Accepted, Superseded, Deprecated. Provenance: Explicitly documented, Git-history supported, Reconstructed from implementation, Needs confirmation.

| ID | Title | Decision status | Rationale provenance |
| --- | --- | --- | --- |
| ADR-001 | Python launcher and local static UI | Implemented / Accepted | Reconstructed from implementation |
| ADR-002 | Local SQLite job store | Implemented / Accepted | Git-history supported |
| ADR-003 | Isolated workspaces | Implemented / Accepted | Git-history supported |
| ADR-004 | Representative sampling and coverage | Implemented / Accepted | Git-history supported |
| ADR-005 | Default-deny interactions | Implemented / Accepted | Reconstructed from implementation |
| ADR-006 | Rich result semantics and provenance | In progress | Reconstructed from working tree |
| ADR-007 | Evidence-bound AI enrichment | Implemented / Accepted | Reconstructed from implementation |
| ADR-008 | Explicit publication | Implemented / Accepted | Explicitly documented |

## ADR-001: Python launcher and local static UI

**Decision status:** Implemented / Accepted
**Rationale provenance:** Reconstructed from implementation
**Context:** The launcher/API and static reports are served/generated in this repository.
**Decision:** Use `src/ui/server.py` as the launcher/API and generate static reports.
**Consequences / trade-offs:** Small deployment boundary and locally reviewable output; UI/API lifecycle is coupled to the Python application.
**Evidence:** `src/ui/server.py`, report generators.
**Related documents:** [Architecture](ARCHITECTURE.md).

## ADR-002: Local SQLite job store

**Decision status:** Implemented / Accepted
**Rationale provenance:** Git-history supported (`506ebed`)
**Context:** Jobs need durable local state and atomic claims.
**Decision:** Use SQLite WAL, immediate transactions, local leases, and worker threads; reject distributed mode.
**Consequences / trade-offs:** Durable local coordination, but no multi-instance safety.
**Evidence:** `src/jobs/store.py`, `src/jobs/worker.py`.
**Related documents:** [Data Model](DATA-MODEL.md), [Architecture](ARCHITECTURE.md).

## ADR-003: Isolated workspaces

**Decision status:** Implemented / Accepted
**Rationale provenance:** Git-history supported (`c9eeda9`)
**Context:** Concurrent/sequential audits must not reuse prior-run artifacts.
**Decision:** Contain website artifacts under validated per-job directories with atomic writes and symlink checks.
**Consequences / trade-offs:** Prevents cross-run contamination but needs durable storage.
**Evidence:** `src/audit/workspace.py`.
**Related documents:** [Data Model](DATA-MODEL.md), [Architecture](ARCHITECTURE.md).

## ADR-004: Representative sampling and coverage

**Decision status:** Implemented / Accepted
**Rationale provenance:** Git-history supported (`5d9646c`)
**Context:** Website evidence needs bounded, repeatable scope.
**Decision:** Deterministically select bounded pages and record collection coverage.
**Consequences / trade-offs:** Predictable cost/clarity, not full-crawl evidence.
**Evidence:** `src/audit/discovery.py`, `tests/test_discovery_scope.py`.
**Related documents:** [Product Specification](PRODUCT-SPECIFICATION.md), [Architecture](ARCHITECTURE.md).

## ADR-005: Default-deny interactions

**Decision status:** Implemented / Accepted
**Rationale provenance:** Reconstructed from implementation
**Context:** Automated audits must avoid changing an audited system's state.
**Decision:** Permit only conservative disclosures/anchors/same-site GET navigation; block forms, accounts, external/custom schemes, and state-changing methods.
**Consequences / trade-offs:** Some behavior remains unmeasured.
**Evidence:** `src/audit/safe_interaction_tester.py`.
**Related documents:** [Product Specification](PRODUCT-SPECIFICATION.md), [Security Operations](SECURITY_OPERATIONS.md).

## ADR-006: Rich result semantics and provenance

**Decision status:** In progress
**Rationale provenance:** Reconstructed from working tree
**Context:** Legacy TRUE/FALSE/N/A output loses distinctions between uncertainty, non-applicability, and collection failure.
**Decision:** Introduce outcome/applicability/measurement, stable IDs, and provenance while retaining workbook compatibility.
**Consequences / trade-offs:** Consumers may diverge until the work is committed and integrated.
**Evidence:** untracked `src/audit/result_model.py`, modified check/report modules, untracked `tests/test_phase2b_evidence.py`.
**Related documents:** [Implementation Plan](IMPLEMENTATION-PLAN.md#in-progress-work), [Data Model](DATA-MODEL.md).

## ADR-007: Evidence-bound AI enrichment

**Decision status:** Implemented / Accepted
**Rationale provenance:** Reconstructed from implementation
**Context:** AI-assisted review is useful only when constrained to auditable evidence.
**Decision:** Use structured, visible-evidence-focused AI review as optional enrichment.
**Consequences / trade-offs:** Provider failure does not establish facts; output requires review.
**Evidence:** `src/gtm_audit/vision_client.py`, `figma_audit/ai_reviewer.py`.
**Related documents:** [Product Requirements](PRODUCT-REQUIREMENTS.md), [Technical Specification](TECHNICAL-SPECIFICATION.md).

## ADR-008: Explicit publication

**Decision status:** Implemented / Accepted
**Rationale provenance:** Explicitly documented
**Context:** Published reports must not accept arbitrary locally edited HTML.
**Decision:** Publish only an explicitly selected immutable machine report.
**Consequences / trade-offs:** Publication is a separate explicit review/deployment step.
**Evidence:** `src/gtm_audit/vercel_static_deploy.py`, [Security Operations](SECURITY_OPERATIONS.md).
**Related documents:** [Architecture](ARCHITECTURE.md), [Technical Specification](TECHNICAL-SPECIFICATION.md).
