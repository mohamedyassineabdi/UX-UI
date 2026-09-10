# UX/UI Auditor

**Status:** Engineer entry point
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** Engineers, UX/UI specialists, and technical stakeholders
**Scope:** Setup and safe orientation. See the linked specifications for detailed behavior.
**Related documents:** [Product Requirements](docs/PRODUCT-REQUIREMENTS.md), [Product Specification](docs/PRODUCT-SPECIFICATION.md), [Technical Specification](docs/TECHNICAL-SPECIFICATION.md).

UX/UI Auditor creates evidence-backed UX/UI audit reports from public websites, uploaded screenshots, Android apps, and Figma files. It combines deterministic and tool-backed checks with optional evidence-constrained AI interpretation. It is not a full-site crawler, WCAG certification, or field-performance product.

## Supported audit modes

| Input | Main path | Output |
| --- | --- | --- |
| Public website URL | Playwright discovery/collection, checks, measurement, scoring | isolated workspace and static report |
| Image uploads | visible-image analysis | static audit report |
| Android app | Appium capture and bounded exploration | mobile evidence and report |
| Figma URL | Figma API ingestion, normalization, checks/detections | Figma report |

## How an audit works

An authenticated request creates a durable job. A local worker runs the selected pipeline, records evidence, applies measurements/checks, derives the five-axis scorecard, and writes a machine audit. Where review is used, the lifecycle is machine audit -> review revision -> validation -> approval -> immutable publication snapshot.

The five axes are Performance & Task Execution, Flow & Architecture, Trust & Accessibility, Visual & UI Consistency, and Content & Microcopy. Scores use applicable, measured pass/fail evidence; warnings are cautions, and incomplete measurement reduces coverage/confidence rather than creating synthetic credit.

## Requirements and installation

- Python 3.10-3.12 and `uv`
- Node.js 20+ for the bundled frontend and audit tooling
- Playwright Chromium
- Appium plus an Android device/emulator for live mobile audits
- Authorized Figma token(s) for Figma audits

```bash
python -m pip install uv==0.9.28
uv sync --frozen
uv run python -m playwright install chromium
npm ci --ignore-scripts
npm run build
```

The React/Vite frontend build is emitted to `src/ui/static/app/`; the Python server serves that production bundle and does not run a Vite server.

Create a git-ignored `.env`. Outside local development, `UX_AUTH_SERVICE_URL` is required. Figma uses `FIGMA_TOKEN` or `FIGMA_TOKENS`; AI/provider and Vercel settings are optional and sensitive. See the [configuration matrix](docs/TECHNICAL-SPECIFICATION.md#configuration-matrix); never commit credentials.

## Run and verify

```bash
uv run python -m src.ui.server --host 127.0.0.1 --port 8787
uv run pytest -q
uv run python -m compileall src figma_audit navigator scripts
docker build --pull=false -t ux-ui-auditor .
```

Website artifacts are under `shared/audits/<job-id>/`; other mode artifacts are under `shared/generated/`. Screenshot and live-mobile jobs are disabled by the supplied Render configuration; Figma remains enabled unless `FIGMA_AUDITS_DISABLED` is set. SQLite is a single-instance job store; persistent criteria/artifacts require external durable storage on ephemeral deployments.

Lighthouse values are laboratory measurements, not CrUX or field Core Web Vitals. Automated accessibility checks and visual-model output require human review and do not establish conformance or factual certainty.

## Documentation map

- [Product requirements](docs/PRODUCT-REQUIREMENTS.md) and [product specification](docs/PRODUCT-SPECIFICATION.md)
- [Technical specification](docs/TECHNICAL-SPECIFICATION.md), [architecture](docs/ARCHITECTURE.md), and [data model](docs/DATA-MODEL.md)
- [Implementation plan](docs/IMPLEMENTATION-PLAN.md), [decisions](docs/DECISIONS.md), [roadmap](docs/ROADMAP.md), and [checkpoint](docs/CHECKPOINT.md)
- [Security operations](docs/SECURITY_OPERATIONS.md)
