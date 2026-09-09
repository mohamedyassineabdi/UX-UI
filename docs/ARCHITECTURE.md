# Architecture and review lifecycle

The Python HTTP server (`src.ui.server`) owns HTTP dispatch, authentication,
ownership checks, request limits, persistent-job wiring, and static-asset
route selection. `src.ui.http_helpers` owns JSON responses, bounded JSON body
parsing, and static-file streaming so those HTTP mechanics are not duplicated
in route dispatch. The server serves the production frontend at `/`; the
frontend build is emitted to `src/ui/static/app/` and is intentionally not
committed.

The audit pipeline creates a job-local workspace, captures evidence and
provenance, applies deterministic and tool-backed checks, then writes the
machine report. The job store and worker preserve queue, lease, cancellation,
timeout, retention, and ownership behaviour independently of the browser UI.

The frontend is built with Vite and uses locally pinned React, ReactDOM and
GSAP. `main.jsx` mounts `App.jsx`; audit submission, polling, review, and
publication are separated into `audit/`, `hooks/`, `review/`, and `api/`.
`api/client.js` owns bearer authentication, API URL construction, transport,
JSON/error conversion, and request IDs. The CSS source is split across
`styles/tokens.css`, `base.css`, `layout.css`, `audit.css`, and `review.css`.
The production server does not run Vite or rely on a third-party framework CDN.

`src.ui.mobile_service` owns pure ADB device-list parsing and Android app
normalization. `server.py` retains command execution, trusted input handling,
route dispatch, authentication, ownership, and dependency wiring.

## Review and publication lifecycle

`Machine audit → structured review → revision → validation → approval →
immutable publication snapshot`

Editing creates an append-only revision. Edit is not validation, validation is
not publication, and approval is not publication. Publication names an
explicit revision, checks eligibility, and writes an immutable snapshot whose
SHA-256 is verified on retrieval. Machine-unreviewed publication remains a
distinct state. Optimistic concurrency conflicts return HTTP 409 and never
overwrite a newer revision.

## Deliberate large-module decisions

| Module | Decision | Reason |
| --- | --- | --- |
| `visual_hierarchy_checks.py` | DEFER | Its evidence/scoring helpers are tightly coupled to Phase 3 methodology and existing characterization tests; a mechanical split risks semantic regression. |
| `figma_audit/reports.py` | KEEP | Active Figma report rendering, evidence image handling, scope and methodology are coupled; it must remain imported and intact. |
| `generate_gtm_report.py` | DEFER | Active report renderer with intertwined safe HTML, evidence, and image-geometry helpers; split only with dedicated renderer characterization coverage. |

## Legacy inventory

No candidate was removed in Phase 4B without a full caller trace. The report
generators, Figma runner, and audit entry points are active or compatibility
surfaces and remain kept. Historical/experimental candidates require a
separate evidence-backed removal change.
