# Technical Specification

**Status:** Committed baseline; in-progress evidence work is explicitly excluded
**Repository baseline:** `main @ 5d9646c4daa221f43c82cd8d477144900193bdb0`
**Last updated:** 2026-09-10
**Audience:** Developers, operators, and maintainers
**Scope:** Runtime contract and component boundaries.
**Related documents:** [Architecture](ARCHITECTURE.md), [Data Model](DATA-MODEL.md), [Decisions](DECISIONS.md), [Security Operations](SECURITY_OPERATIONS.md).

## Runtime and dependency matrix

| Area | Baseline |
| --- | --- |
| Runtime | Python >=3.10,<3.13; Node 20 in Docker for Vercel tooling |
| Dependency source | `pyproject.toml` and `uv.lock`; `requirements.txt` is compatibility export |
| Browser/mobile | Playwright 1.43; Appium Python Client 5.1.3; Selenium 4.32 |
| Parsing/models/output | BeautifulSoup/lxml, Pydantic, Pillow, openpyxl |
| UI | Python `BaseHTTPRequestHandler` plus local static assets; no separate frontend build |
| Container | matching Playwright Python image, non-root `auditor`, healthcheck |

## Components, execution, and storage

| Component | Responsibility |
| --- | --- |
| `src/ui/server.py` | HTTP, auth/ownership, validation, queueing, subprocess execution, report packaging |
| `src/jobs/` | SQLite store, event log, atomic claims, leases/heartbeats, local worker threads, retention |
| `navigator/`, `src/main.py`, `src/audit/` | discovery, Playwright collection, checks, workspace and workbook export |
| `src/gtm_audit/`, `src/report/` | score/report payload generation and static report rendering |
| `src/mobile_audit/` | Appium extraction, bounded exploration, mobile report input |
| `figma_audit/` | Figma ingestion, normalization, detections/rules, annotations and report support |

One application instance runs local worker threads and pipeline subprocesses. SQLite WAL/`BEGIN IMMEDIATE` serializes writers on that host; `UX_DEPLOYMENT_MODE=distributed` intentionally fails. Job/event truth is SQLite; website artifacts are under `shared/audits/<job-id>` and other-mode artifacts under `shared/generated/`. Static reports are derived artifacts, not database rows.

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

Bearer authentication and owner checks protect APIs/reports/artifacts. Public health/readiness and launcher assets are exceptions. URL validation, DNS pinning, redirect/browser guards, request limits, CORS allowlisting, CSP, TLS restrictions and security headers provide trust boundaries. Job events and request IDs support diagnosis; `/ready` also requires worker/Playwright availability.

## Deployment, testing, and constraints

Docker and the supplied Render deployment run a single application instance. Persistence across an ephemeral deployment depends on externally provided durable storage for custom criteria and retained artifacts. Render disables screenshot and live-mobile jobs, skips vision, and does not disable Figma. CI runs locked tests, compile/import checks, Gitleaks, and Docker gates.

**In progress - present in the working tree but not part of the repository baseline:** `src/audit/result_model.py` and related changed consumers introduce richer evidence/provenance state. See [ADR-006](DECISIONS.md#adr-006-rich-result-semantics-and-provenance) and do not rely on it as a baseline API contract.
