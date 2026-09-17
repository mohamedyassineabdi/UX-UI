# Technical Specification

**Status:** Current implementation
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** Developers, operators, and maintainers
**Scope:** Runtime contract and component boundaries.
**Related documents:** [Architecture](ARCHITECTURE.md), [Data Model](DATA-MODEL.md), [Decisions](DECISIONS.md), [Security Operations](SECURITY_OPERATIONS.md).

## Runtime and dependency matrix

| Area | Baseline |
| --- | --- |
| Runtime | Python >=3.10,<3.13; Node.js 20+ for bundled frontend/tooling |
| Dependency source | `pyproject.toml` and `uv.lock`; `requirements.txt` is compatibility export |
| Browser/mobile | Playwright 1.43; Appium Python Client 5.1.3; Selenium 4.32 |
| Parsing/models/output | BeautifulSoup/lxml, Pydantic, Pillow, openpyxl |
| UI | React/Vite frontend source, built into `src/ui/static/app/` and served by Python |
| Container | matching Playwright Python image, non-root `auditor`, healthcheck |

## Components, execution, and storage

| Component | Responsibility |
| --- | --- |
| `src/ui/server.py` | HTTP, auth/ownership, validation, queueing, subprocess execution, report packaging |
| `src/jobs/` | SQLite store, event log, atomic claims, leases/heartbeats, local worker threads, retention |
| `src/ui/frontend/` | React audit/review UI, API clients, hooks and CSS source; `vite.config.mjs` builds production assets |
| `navigator/`, `src/main.py`, `src/audit/` | discovery, Playwright collection, result semantics, Axe/Lighthouse/visual measurements, checks and workspace |
| `src/gtm_audit/`, `src/report/` | evidence-aware scoring, machine/reviewed report generation and static rendering |
| `src/mobile_audit/` | Appium extraction, bounded exploration, mobile report input |
| `figma_audit/` | Figma ingestion, normalization, detections/rules, annotations and report support |

One application instance runs local worker threads and pipeline subprocesses. SQLite WAL/`BEGIN IMMEDIATE` serializes writers on that host; `UX_DEPLOYMENT_MODE=distributed` intentionally fails. Schema version 3 adds review revision/event and publication-snapshot storage. Website artifacts are under `shared/audits/<job-id>` and other-mode artifacts under `shared/generated/`. Static reports are derived artifacts, not database rows.

## Configuration matrix

| Variable/group | Purpose | Required / default | Applies | Sensitive |
| --- | --- | --- | --- | --- |
| `HOST`, `PORT` | listener | defaults `0.0.0.0`, `8787` | runtime | no |
| `UX_AUTH_SERVICE_URL` | portal `/auth/me` | required outside development | protected API | no |
| `UX_DEV_AUTH_BYPASS` | loopback development bypass | default `0`; forbidden staging/production | local only | no |
| `UX_MAX_*` | request/upload limits | safe defaults defined in server | UI | no |
| `UX_ALLOWED_OUTBOUND_PORTS`, `UX_DNS_TIMEOUT_SECONDS` | SSRF/DNS policy | defaults `80,443`, `3` | website | no |
| `UX_JOB_DATABASE_URL`, `UX_AUDIT_WORKER_*` | SQLite location, workers, leases, queue | SQLite default; worker default `1` | jobs | no |
| `UX_AUDIT_*TIMEOUT*`, retention/storage/page/coverage | run limits and lifecycle | safe defaults in server/config | audits | no |
| `FIGMA_TOKEN`/`FIGMA_TOKENS`, `FIGMA_*` | Figma authorization/fetch | token required for live Figma | Figma | yes for tokens |
| `AI_REVIEW_*`, `OLLAMA_*`, provider API keys | optional model review | provider-dependent | AI paths | keys sensitive |
| `APPIUM_SERVER_URL` | local mobile endpoint | default local endpoint | mobile | no |
| `VERCEL_TOKEN` | explicit publication | optional | publication | yes |

## Integrations, resilience, and security

External integrations are portal auth, public websites, Figma API, optional model providers, Appium/ADB, and optional Vercel CLI. Stage/total deadlines and bounded transient retries are configurable. Lease expiry records `interrupted`; it never silently restarts an audit.

Bearer authentication and owner checks protect APIs/reports/artifacts/reviews/publications. Public health/readiness and launcher assets are exceptions. URL validation, DNS pinning, redirect/browser guards, request limits, CORS allowlisting, CSP, TLS restrictions and security headers provide trust boundaries. Job events and request IDs support diagnosis; `/ready` also requires worker/Playwright availability.

## Deployment, testing, and constraints

Docker and the supplied Render deployment run a single application instance. Docker installs npm dependencies and runs `npm run build`; CI likewise runs `npm ci --ignore-scripts`, builds the frontend, and checks that no framework CDN references remain in the production bundle. Persistence across an ephemeral deployment depends on externally provided durable storage for custom criteria and retained artifacts. Render disables screenshot and live-mobile jobs, skips vision, and does not disable Figma.

Measurement and scoring are current baseline behavior: result semantics preserve outcome/applicability/measurement/provenance; Axe and Lighthouse outputs are stored job-locally; scoring uses applicable measured pass/fail rules and measurement coverage. Methodology v2 uses `src/gtm_audit/rule_registry.py` as the authoritative one-primary-axis registry, with non-scoring secondary tags, evidence grades, mode applicability, and logical-defect deduplication. `SHEET_AXIS_MAP` is retained only for explicit methodology-v1 interpretation; unknown v2 rules are reportable but unscored. Lighthouse is laboratory-only and its aggregate category is report-only; visual-model conclusions remain probabilistic and independently unscored. Review revisions are append-only and publication records immutable snapshots. See [ADR-006](DECISIONS.md#adr-006-rich-result-semantics-and-provenance).
