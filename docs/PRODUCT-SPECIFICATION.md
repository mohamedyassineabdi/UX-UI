# Product Specification

**Status:** Current baseline behavior
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** UX/UI specialists, product stakeholders, developers, and test authors
**Scope:** Observable behavior. See [Technical Specification](TECHNICAL-SPECIFICATION.md) for implementation.
**Related documents:** [Requirements](PRODUCT-REQUIREMENTS.md), [Architecture](ARCHITECTURE.md), [Data Model](DATA-MODEL.md).

## Core terminology

| Term | Meaning |
| --- | --- |
| Audit / audit mode | An assessment run and its input path: website, screenshot, Figma, or Android/mobile. |
| Job / workspace | A durable request record / the isolated filesystem area for one run. |
| Criterion, check, rule | An evaluation expectation / its executable assessment / the implementation unit that performs it. |
| Evidence / finding / severity | Captured support / a reportable observation / low, medium, or high practical impact. |
| Collection coverage | Completed selected website pages divided by selected pages. |
| Measurement coverage | Measured applicable rule weight divided by applicable rule weight. It is separate from collection coverage and affects confidence/coverage, not compliance credit. |
| Outcome, applicability, measurement state | Respectively pass/fail/warning/unknown; applicable/not applicable/unknown; measured/not measured/collection failed. Legacy workbook labels are adapters only. |
| Provenance | How a finding is attributed: verified, inferred, unresolved, or site-wide aggregate. |
| Score / report / publication | Evidence-aware five-axis result / generated machine audit or reviewed report / immutable snapshot of an explicit revision. |
| GTM | Legacy internal label for the decision-oriented report payload; use "audit report" in product-facing communication. |

## Common job lifecycle and result behavior

Baseline lifecycle: `queued -> running -> completed | failed | cancelled`; a lease-expired running job becomes `interrupted` and is not automatically rerun. Queued cancellation is immediate; running cancellation requests termination of application-owned processes. Job progress is stage-level. Retention can delete terminal artifacts while retaining tombstone metadata.

After a machine audit completes, a reviewer may create an append-only revision. Revision states are `in_review`, `changes_requested`, `validated`, and `approved`; validation and approval do not themselves publish a report. Publication writes an immutable snapshot and can remain a distinct machine-unreviewed path. Conflicting revision edits return HTTP 409 rather than overwrite a newer revision.

Result semantics preserve deterministic rule/finding/evidence identifiers, outcome, applicability, measurement, and provenance. Collection coverage is page collection; measurement coverage is rule measurement. Scores include applicable measured pass/fail rules only; warnings are cautions, and not-applicable, unknown, not-measured, and collection-failed items do not receive score credit. Axe is standards automation; Lighthouse values are laboratory measurements, not field Core Web Vitals. Visual-model output is probabilistic and schema-validated.

## Cross-cutting acceptance criteria

- `PS-COM-AC-001`: An authenticated request with valid mode-specific input creates a queued job; invalid or unsafe input does not create a runnable job. Evidence: `src/ui/server.py`, `tests/test_auth.py`, `tests/test_upload_security.py`, and `tests/test_server_security.py`.
- `PS-COM-AC-002`: Job, report, artifact, review, cancellation, and publication access enforce authenticated ownership; publication does not accept arbitrary edited HTML. Evidence: `src/security/auth.py`, `src/ui/server.py`, `tests/test_auth.py`, `tests/test_publication_security.py`, and `tests/test_review_workflow.py`.
- `PS-COM-AC-003`: Jobs only make allowed lifecycle transitions and end as completed, failed, cancelled, or interrupted according to the executed/cancelled/lease-expired outcome. Evidence: `src/jobs/models.py`, `src/jobs/store.py`, and `tests/test_job_queue.py`.
- `PS-REP-AC-001`: Findings retain evidence, severity, result state, and verified/inferred/unresolved/site-wide provenance rather than silently assigning unsupported attribution. Evidence: `src/audit/result_semantics.py`, `tests/test_phase2b_semantics.py`.
- `PS-REP-AC-002`: AI-assisted review remains evidence-constrained and must not be represented as an established fact when supporting visible evidence is absent. Evidence: `src/gtm_audit/vision_client.py`, `figma_audit/ai_reviewer.py`; no direct automated acceptance test is established.
- `PS-SCORE-AC-001`: The configured five-axis taxonomy uses applicable measured pass/fail evidence, with explicit mapping and measurement coverage. Evidence: `src/gtm_audit/scoring.py`, `tests/test_phase3a_scoring.py`.
- `PS-REV-AC-001`: Review revisions are append-only; validation, approval, and immutable publication are distinct states. Evidence: `src/audit/review_schema.py`, `src/jobs/store.py`, `tests/test_review_workflow.py`.

## Website audit

**Preconditions and inputs.** An authenticated user submits a public HTTP(S) URL. The URL must resolve to public addresses on allowed ports and contain no credentials.

**Processing.** Discovery considers homepage/navigation/footer and sitemap candidates; same-site, robots, authentication-page, duplicate, and page-cap rules yield a deterministic representative sample. Playwright collects rendered/extracted evidence, screenshots, and conservative interaction observations. Forms, account/auth flows, downloads, external/custom-scheme destinations, and state-changing requests are blocked.

**Outputs and limitations.** The workspace contains collection artifacts, checks and a static report. `PS-WEB-AC-001`: an under-threshold completed/selected ratio must be represented as incomplete coverage. `PS-WEB-AC-002`: no blocked action may be silently reported as a successful interaction. This is not a full-site crawl or field-performance audit.

## Screenshot audit

**Preconditions and inputs.** Authenticated uploads must satisfy count, MIME/image, byte, dimension, and pixel limits; users may label screenshots and select website/mobile surface type.

**Processing and output.** The system creates a decision-oriented report payload and static report from visible imagery. The current Render configuration disables this mode.

**Limitations/acceptance.** It cannot establish hidden behavior, semantics, network performance, or unseen flow states. `PS-SHOT-AC-001`: invalid uploads must not create a runnable job. `PS-SHOT-AC-002`: deployment-disabled mode must fail with an actionable job error.

## Figma audit

**Preconditions and inputs.** A supported Figma URL and configured authorized token(s) are required.

**Processing and output.** The pipeline fetches/caches a bundle, normalizes pages, frames, nodes, components and tokens, runs rules/detections, assesses evidence quality, and attempts annotations before producing a report.

**Limitations/acceptance.** Static design evidence does not prove runtime implementation or behavior. `PS-FIG-AC-001`: missing/unusable authorization must fail the job rather than issue a successful audit. Figma can be disabled by `FIGMA_AUDITS_DISABLED`, but the current Render configuration does not set that flag.

## Android/mobile audit

**Preconditions and inputs.** A trusted local Appium endpoint plus compatible Android device/emulator and package/activity information are required.

**Processing and output.** The app path records hierarchy, screenshots, tappables and screen fingerprints, performs bounded safe exploration/scrolling, then produces report input and a static report.

**Limitations/acceptance.** Live mobile mode is disabled in current Render configuration and cannot operate without its local runtime. `PS-MOB-AC-001`: unavailable/disabled runtime must surface a job failure, not a completed result.

## PRD traceability

| PRD requirement | Specification section | Acceptance criteria | Implementation / test evidence |
| --- | --- | --- | --- |
| `PRD-FR-001` | Cross-cutting acceptance criteria; all four audit-mode sections | `PS-COM-AC-001` | `src/ui/server.py`; `tests/test_auth.py`, `tests/test_upload_security.py`, `tests/test_server_security.py` |
| `PRD-FR-002` | All four audit-mode sections | `PS-WEB-AC-001`, `PS-SHOT-AC-001`, `PS-SHOT-AC-002`, `PS-FIG-AC-001`, `PS-MOB-AC-001` | `scripts/run_pipeline.py`, `src/figma_audit_runner.py`, `src/mobile_audit/run_mobile_audit.py`, `src/gtm_audit/generate_screenshot_gtm_audit.py` |
| `PRD-FR-003` | Website audit | `PS-WEB-AC-001` | `src/audit/discovery.py`, `tests/test_discovery_scope.py`, `tests/test_website_pipeline_isolation.py` |
| `PRD-FR-004` | Cross-cutting acceptance criteria; common result behavior | `PS-REP-AC-001` | `src/audit/result_semantics.py`, `tests/test_phase2b_semantics.py` |
| `PRD-FR-005` | Cross-cutting acceptance criteria | `PS-SCORE-AC-001` | `src/gtm_audit/scoring.py`, `tests/test_phase3a_scoring.py` |
| `PRD-FR-006` | Common job lifecycle and result behavior; cross-cutting acceptance criteria | `PS-COM-AC-002`, `PS-COM-AC-003`, `PS-REV-AC-001` | `src/jobs/models.py`, `src/jobs/store.py`, `tests/test_job_queue.py`, `tests/test_review_workflow.py` |
| `PRD-NFR-001` | Cross-cutting acceptance criteria | `PS-REP-AC-002` | `src/audit/measurement.py`, `src/audit/vlm_schema.py`, `src/gtm_audit/vision_client.py`; no direct automated acceptance test for this complete criterion |
| `PRD-NFR-002` | Website audit | `PS-WEB-AC-002` | `src/security/network_policy.py`, `src/audit/safe_interaction_tester.py`, `tests/test_network_policy.py` |
| `PRD-NFR-003` | Common job lifecycle and result behavior; cross-cutting acceptance criteria | `PS-COM-AC-002`, `PS-COM-AC-003` | `src/security/auth.py`, `src/ui/server.py`, `src/jobs/store.py`, `tests/test_auth.py`, `tests/test_publication_security.py`, `tests/test_job_queue.py` |

## Errors and edge cases

Common errors include authentication failure, invalid/unsafe inputs, queue/storage capacity, external provider failure, timeout, cancellation, and missing local runtime. In each case, a job must remain inspectable as failed/cancelled/interrupted rather than becoming a false success.
