# Analytics

**Status:** Current observability inventory and proposed-only product analytics guidance
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Product managers, operators, and engineers
**Scope:** Distinguishes current operational records/audit metrics from product telemetry.
**Related documents:** [Data Model](DATA-MODEL.md), [Database Specification](DATABASE-SPECIFICATION.md), [Content Guidelines](CONTENT-GUIDELINES.md), [Security](SECURITY.md).

## Current state: no dedicated product analytics

No application source integration for an analytics, telemetry, error-monitoring, or product-event platform was found. Package-lock transitive entries alone are not treated as enabled telemetry. The product does not currently track users, funnels, dashboards, approved KPIs, or analytics events.

SQLite does persist operational job events, state/progress, worker/lease data, review events, revisions, and publication records. These are operational/product-state records, not behavioral analytics. Audit outputs also contain collection coverage, measurement coverage, five-axis scores, Axe/Lighthouse measurements, and evidence/provenance. Those describe the audited product, not use of UX/UI Auditor.

## Proposed / needs approval

If product analytics is approved, a minimal event model could include audit creation/completion/failure/cancellation, revision creation, validation, approval, and publication outcomes. Safe properties would be mode, terminal state, elapsed bucket, coverage bucket, and deployment mode. Do not send bearer tokens, credentials, raw uploads, report content, full target URLs, provider keys, or unapproved user identifiers.

Candidate operational metrics include time to reviewable report and terminal-state counts; candidate product metrics include audit completion, review progression, and publication progression. Score calibration/KPI targets, reviewer acceptance metrics, and any funnel/dashboard are **proposed** and require product/privacy approval. No privacy policy or consent mechanism is implemented by this repository.
