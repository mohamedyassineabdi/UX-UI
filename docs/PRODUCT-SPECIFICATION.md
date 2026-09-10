# Product Specification

**Status:** Baseline behavior plus explicitly marked in-progress behavior
**Repository baseline:** `main @ 5d9646c4daa221f43c82cd8d477144900193bdb0`
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
| Measurement coverage | A formal cross-check notion of the proportion of applicable items actually measured; it is not collection coverage. **In progress - present in the working tree but not part of the repository baseline.** The baseline has rule-level `coverage` values in selected visual-hierarchy checks, but does not establish this shared result-model contract. |
| Outcome, applicability, measurement state | Respectively pass/fail/warning/unknown; applicable/not applicable/unknown; measured/not measured/collection failed. **In progress:** these richer website semantics exist only in the working tree, not the baseline. |
| Provenance | How a finding is attributed: verified, inferred, unresolved, or site-wide aggregate. **In progress:** richer provenance is working-tree-only. |
| Score / report / publication | Evidence-dependent axis estimate / generated static output / explicit deployment of a selected machine report. |
| GTM | Legacy internal label for the decision-oriented report payload; use "audit report" in product-facing communication. |

## Common job lifecycle and result behavior

Baseline lifecycle: `queued -> running -> completed | failed | cancelled`; a lease-expired running job becomes `interrupted` and is not automatically rerun. Queued cancellation is immediate; running cancellation requests termination of application-owned processes. Job progress is stage-level. Retention can delete terminal artifacts while retaining tombstone metadata.

Baseline check/report consumers may use legacy TRUE/FALSE/N/A values. **In progress - present in the working tree but not part of the repository baseline:** result state, deterministic IDs, provenance, and review markers preserve pass/fail/warning/unknown, applicability, and measurement distinctions. Until committed and fully integrated, reports must not claim that richer contract as baseline behavior.

## Cross-cutting acceptance criteria

- `PS-COM-AC-001`: An authenticated request with valid mode-specific input creates a queued job; invalid or unsafe input does not create a runnable job. Evidence: `src/ui/server.py`, `tests/test_auth.py`, `tests/test_upload_security.py`, and `tests/test_server_security.py`.
- `PS-COM-AC-002`: Job, report, artifact, cancellation, and publication access enforce authenticated ownership; the report publication path does not accept arbitrary edited HTML. Evidence: `src/security/auth.py`, `src/ui/server.py`, `tests/test_auth.py`, and `tests/test_publication_security.py`.
- `PS-COM-AC-003`: Jobs only make allowed lifecycle transitions and end as completed, failed, cancelled, or interrupted according to the executed/cancelled/lease-expired outcome. Evidence: `src/jobs/models.py`, `src/jobs/store.py`, and `tests/test_job_queue.py`.
- `PS-REP-AC-001`: **In progress - present in the working tree but not part of the repository baseline.** Rich findings retain evidence, severity, and verified/inferred/unresolved/site-wide attribution rather than silently assigning unsupported provenance. Evidence is implementation plus the untracked `tests/test_phase2b_evidence.py`; no baseline test verifies this contract.
- `PS-REP-AC-002`: AI-assisted review remains evidence-constrained and must not be represented as an established fact when supporting visible evidence is absent. Evidence: `src/gtm_audit/vision_client.py` and `figma_audit/ai_reviewer.py`; no direct automated acceptance test is established.
- `PS-SCORE-AC-001`: The current five-axis audit taxonomy is the configured/report-generation taxonomy: Performance & Task Execution, Flow & Architecture, Trust & Accessibility, Visual & UI Consistency, and Content & Microcopy. Evidence: `shared/config/audit_axes.json` and `src/gtm_audit/generate_gtm_audit.py`; no direct automated acceptance test is established.

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
| `PRD-FR-004` | Cross-cutting acceptance criteria; common result behavior | `PS-REP-AC-001` | In-progress implementation only: `src/audit/result_model.py`, modified consumers, untracked `tests/test_phase2b_evidence.py`; no baseline contract/test |
| `PRD-FR-005` | Cross-cutting acceptance criteria | `PS-SCORE-AC-001` | `shared/config/audit_axes.json`, `src/gtm_audit/generate_gtm_audit.py`; no direct automated acceptance test |
| `PRD-FR-006` | Common job lifecycle and result behavior; cross-cutting acceptance criteria | `PS-COM-AC-002`, `PS-COM-AC-003` | `src/jobs/models.py`, `src/jobs/store.py`, `src/jobs/worker.py`, `tests/test_job_queue.py`, `tests/test_auth.py`, `tests/test_publication_security.py` |
| `PRD-NFR-001` | Cross-cutting acceptance criteria | `PS-REP-AC-002` | `src/gtm_audit/vision_client.py`, `figma_audit/ai_reviewer.py`; implementation-only, no direct automated acceptance test |
| `PRD-NFR-002` | Website audit | `PS-WEB-AC-002` | `src/security/network_policy.py`, `src/audit/safe_interaction_tester.py`, `tests/test_network_policy.py` |
| `PRD-NFR-003` | Common job lifecycle and result behavior; cross-cutting acceptance criteria | `PS-COM-AC-002`, `PS-COM-AC-003` | `src/security/auth.py`, `src/ui/server.py`, `src/jobs/store.py`, `tests/test_auth.py`, `tests/test_publication_security.py`, `tests/test_job_queue.py` |

## Errors and edge cases

Common errors include authentication failure, invalid/unsafe inputs, queue/storage capacity, external provider failure, timeout, cancellation, and missing local runtime. In each case, a job must remain inspectable as failed/cancelled/interrupted rather than becoming a false success.
