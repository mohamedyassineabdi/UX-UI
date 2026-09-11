# API Specification

**Status:** Current committed API contract
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Frontend, backend, integration, and test engineers
**Scope:** HTTP contract implemented by `src/ui/server.py`; this is not an OpenAPI document.
**Related documents:** [Technical Specification](TECHNICAL-SPECIFICATION.md), [Database Specification](DATABASE-SPECIFICATION.md), [Security](SECURITY.md), [Product Specification](PRODUCT-SPECIFICATION.md).

## Scope and conventions

The React frontend calls the Python `BaseHTTPRequestHandler` application directly. There is no API version prefix or published OpenAPI schema. The listener uses `HOST`/`PORT` (defaults `0.0.0.0`/`8787`). JSON responses use `application/json`; failures normally use an `error` string and internal-error/conflict responses may also include `requestId`.

`Authorization: Bearer <portal-session-token>` is required for every endpoint except `/health`, `/ready`, `/`, and static assets. Authenticated job, report, artifact, review, and publication access is owner-scoped; absent or non-owned objects intentionally return `404`. `POST /api/criteria*` additionally requires the `admin` role. `OPTIONS` permits only origins listed in `UX_CORS_ALLOWED_ORIGINS`.

## Endpoint inventory

| Method | Path | Access | Contract / success | Principal error cases | Evidence |
| --- | --- | --- | --- | --- | --- |
| GET | `/health` | public | Liveness JSON with job-store/storage/browser checks; `200` unless core liveness checks fail | `503` degraded | `src/ui/server.py` |
| GET | `/ready` | public | Readiness JSON; also requires healthy worker and available browser | `503` degraded | `src/ui/server.py` |
| GET | `/` | public | React/Vite built `index.html` | `404` if build asset absent | `src/ui/server.py` |
| GET | `/static/<path>` | public, contained path | Static asset | `404` for missing/out-of-root path | `src/ui/server.py`, `tests/test_frontend_security.py` |
| GET | `/api/criteria` | authenticated | Current criteria payload and source | `401`, `500` | `src/ui/server.py` |
| POST | `/api/criteria` | admin | Validate and save criteria JSON | `400`, `401`, `403`, `500` | `src/ui/server.py`, `tests/test_server_security.py` |
| POST | `/api/criteria/reset` | admin | Restore default criteria payload | `401`, `403`, `500` | `src/ui/server.py` |
| GET | `/api/capabilities` | authenticated | `{detailedAuditAvailable}` | `401` | `src/ui/server.py` |
| GET | `/api/mobile/discovery` | authenticated | Device/current-app/defaults discovery payload | `401`, `500` | `src/ui/server.py` |
| POST | `/api/audits` | authenticated, rate-limited | Queue a website, Figma, mobile, or multipart screenshot job; `202` job snapshot | `400`, `401`, `429`, `503`, `500` | `src/ui/server.py`, `tests/test_auth.py`, `tests/test_upload_security.py` |
| GET | `/api/audits/<jobId>` | owner | Current job snapshot, including logs and review summary | `401`, `404` | `src/ui/server.py`, `tests/test_job_queue.py` |
| POST | `/api/audits/<jobId>/cancel` | owner | Request cancellation; queued jobs become cancelled immediately | `401`, `404` | `src/ui/server.py`, `tests/test_job_queue.py` |
| GET | `/api/audits/<jobId>/review` | owner | Current review summary plus revisions | `401`, `404` | `src/ui/server.py`, `tests/test_review_workflow.py` |
| POST | `/api/audits/<jobId>/revisions` | owner | Create append-only revision; `201` | `400`, `401`, `404`, `409` stale expected revision | `src/ui/server.py`, `tests/test_review_workflow.py` |
| POST | `/api/audits/<jobId>/validate` | owner | Transition revision to `validated` | `400`, `401`, `404` | `src/ui/server.py`, `tests/test_review_workflow.py` |
| POST | `/api/audits/<jobId>/approve` | owner | Transition validated revision to `approved` | `400`, `401`, `404` | `src/ui/server.py`, `tests/test_review_workflow.py` |
| GET | `/api/audits/<jobId>/review-report/<revisionId>` | owner | Rendered review HTML for that revision | `401`, `404` | `src/ui/server.py`, `tests/test_review_ui_contract.py` |
| POST | `/api/audits/<jobId>/publish` | owner | Create publication record and invoke configured publication; reviewed or machine-unreviewed path | `400`, `401`, `404`, `409`, `502` | `src/ui/server.py`, `tests/test_publication_security.py` |
| GET | `/audits/<jobId>/...` | owner | Generated local report asset | `401`, `404` | `src/ui/server.py`, `tests/test_server_security.py` |
| GET | `/artifacts/<relativePath>` | owner, path-contained | Job artifact | `401`, `404` | `src/ui/server.py`, `tests/test_server_security.py` |

## Request shapes

| Audit type / content type | Required input | Optional input / constraints |
| --- | --- | --- |
| Website JSON | `auditType: "website"`, `url` | `mode` is `gtm` (default) or `detailed`; detailed mode requires a configured workbook template. URLs must be public HTTP(S), credential-free, and use allowed ports. |
| Figma JSON | `auditType: "figma"`, `figmaUrl` (or `url`) | A supported Figma URL and configured Figma credentials are required at execution. |
| Mobile JSON | `auditType: "mobile"`, `appPackage`, `appActivity` | `appLabel`, `appiumUrl`, `deviceName`, `platformVersion`, `udid`; trusted local Appium URL required. |
| Screenshot multipart | `auditType=screenshot`, screenshot files | `siteName`, `surfaceType` (`website` or mobile surface), JSON `screenshotLabels`; multipart is rejected for other types. |

Screenshot uploads are bounded by `UX_MAX_UPLOAD_COUNT`, `UX_MAX_UPLOAD_BYTES`, `UX_MAX_IMAGE_DIMENSION`, and `UX_MAX_IMAGE_PIXELS`; the server validates MIME/image content before queueing. Body limits are controlled by `UX_MAX_JSON_BODY_BYTES` and `UX_MAX_MULTIPART_BODY_BYTES`.

## Job, review, and publication behavior

Job states are `queued`, `running`, `completed`, `failed`, `cancelled`, and `interrupted`. A worker lease expiration is persisted as `interrupted` and is not automatically retried. Cancellation of a running job sets a cancellation request; application-owned execution observes it.

`POST /revisions` requires `findingChanges` and an `expectedRevisionId` (plus optional reason accepted by the review payload validator). Revision creation is optimistic: an outdated expected revision receives `409`. Review transitions are `in_review -> changes_requested | validated`, `changes_requested -> in_review`, and `validated -> approved`.

`POST /publish` accepts an optional 32-character `revisionId`. A supplied revision must be `validated` or `approved`, producing a reviewed immutable snapshot. Omitting it creates a separate `machine_unreviewed` snapshot. The API does not accept arbitrary client-supplied report HTML.

## Limitations

There is no URL-versioned API, OpenAPI artifact, documented idempotency key, or pagination contract. Clients must use the routes and response shapes implemented here; stable persisted fields are specified in [Database Specification](DATABASE-SPECIFICATION.md).
