# UX/UI Auditor

Local audit tool for websites, Android mobile apps, uploaded screenshots, and Figma files. The launcher can crawl pages, capture evidence, run UX/UI checks, score the experience, and generate static reports that can be reviewed locally or deployed.

## What It Audits

- Website URLs: crawls representative pages, captures screenshots and page evidence, measures performance KPIs, checks accessibility, and generates an audit report.
- Uploaded screenshots: builds an audit from provided visual evidence when live crawling is not available.
- Android apps: connects through Appium, captures visible screens, explores safe navigation paths, and produces a mobile audit.
- Figma links: fetches the Figma file through the Figma API, analyzes frames/components, captures design evidence, and generates an editable audit report.

The current UX/UI scoring model uses five axes:

- Performance & Task Execution
- Flow & Architecture
- Trust & Accessibility
- Visual & UI Consistency
- Content & Microcopy

## Requirements

- Python 3.10-3.12
- Node.js if you want to use the npm script shortcuts
- Chromium for Playwright
- Appium server and Android emulator/device for mobile audits
- Figma personal access token for Figma audits

Install the exact frozen Python environment (the canonical inputs are `pyproject.toml` and `uv.lock`):

```bash
python -m pip install uv==0.9.28
uv sync --frozen
uv run python -m playwright install chromium
```

The project uses Python modules directly, so `npm install` is only needed if you later add Node dependencies. The existing npm scripts are convenience wrappers around Python commands.

## Environment

Create a local `.env` file. It is ignored by git.

```env
# Portal authentication (required in staging/production)
APP_ENV=development
UX_ENVIRONMENT=
UX_AUTH_SERVICE_URL=http://127.0.0.1:8000/api/v1
UX_AUTH_CONNECT_TIMEOUT_SECONDS=2
UX_AUTH_READ_TIMEOUT_SECONDS=5
UX_CORS_ALLOWED_ORIGINS=http://127.0.0.1:8787,http://localhost:8787
UX_DEV_AUTH_BYPASS=0
AUDIT_BROWSER_IGNORE_HTTPS_ERRORS=0
APPIUM_SERVER_URL=http://127.0.0.1:4723

# Security limits (shown defaults)
UX_MAX_JSON_BODY_BYTES=1048576
UX_MAX_MULTIPART_BODY_BYTES=26214400
UX_MAX_UPLOAD_COUNT=10
UX_MAX_UPLOAD_BYTES=8388608
UX_MAX_IMAGE_DIMENSION=8000
UX_MAX_IMAGE_PIXELS=40000000
UX_RATE_LIMIT_PER_MINUTE=120
UX_AUDIT_CREATE_RATE_LIMIT_PER_MINUTE=5
UX_ALLOWED_OUTBOUND_PORTS=80,443
UX_DNS_TIMEOUT_SECONDS=3

# Required for Figma audits
FIGMA_TOKEN=figd_your_personal_access_token

# Optional: rotate across several Figma tokens for larger files
FIGMA_TOKENS=figd_token_1,figd_token_2

# Optional Figma network settings
FIGMA_VERIFY_SSL=true
FIGMA_CA_BUNDLE=
FIGMA_TRUST_ENV_PROXY=false

# Optional AI review/enrichment
AI_REVIEW_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=
OLLAMA_VISION_MODEL=llama3.2-vision

# Optional report deployment
VERCEL_TOKEN=
```

`UX_DEV_AUTH_BYPASS=1` is available only for loopback-bound local development. It is off by default, prints a prominent warning, and is rejected in staging/production. Production startup fails clearly if `UX_AUTH_SERVICE_URL` is absent. Bearer tokens are read from the existing portal session storage and are never accepted in URLs.

If your company proxy or antivirus breaks TLS validation for the Figma API, set `FIGMA_CA_BUNDLE` to the local CA certificate bundle path instead of disabling SSL verification.

## Run The Local UI

```bash
uv run python -m src.ui.server --host 127.0.0.1 --port 8787
```

Then open the URL printed by the server, usually:

```text
http://127.0.0.1:8787/
```

From the launcher you can start website, mobile, screenshot, or Figma audits depending on the available inputs and environment variables.

## CLI Commands

Website audit:

```bash
python scripts/run_pipeline.py https://example.com --mode gtm
```

Website audit with Vercel deployment:

```bash
python scripts/run_pipeline.py https://example.com --mode gtm --deploy-vercel
```

Figma audit:

```bash
python -m src.figma_audit_runner "https://www.figma.com/design/FILE_KEY/Project?node-id=0-1" --job-id figma-test
```

Equivalent npm shortcut:

```bash
npm run audit:figma -- "https://www.figma.com/design/FILE_KEY/Project?node-id=0-1" --job-id figma-test
```

Mobile audit:

```bash
python -m src.mobile_audit.run_mobile_audit --app-package your.package.name --app-activity your.MainActivity
```

Screenshot-based audit:

```bash
python -m src.gtm_audit.generate_screenshot_gtm_audit
```

Some module and output names still contain legacy internal naming. They are technical names only and do not need to be used as client-facing audit language.

## Figma Audit Notes

Figma audits require `FIGMA_TOKEN` or `FIGMA_TOKENS`. The token must have access to the target file.

Supported Figma URL forms include:

- `https://www.figma.com/file/...`
- `https://www.figma.com/design/...`
- `https://www.figma.com/proto/...`
- `https://www.figma.com/board/...`

Generated reports may still be edited for local review. Phase 0 publication intentionally publishes only the immutable machine-generated report; unrestricted edited HTML is never sent to or accepted by the server.

## Generated Output

Website audit artifacts are written to a deterministic job workspace and are ignored by git:

```text
shared/audits/<job-id>/
```

The server supplies the job ID. Manual website runs receive a unique `manual-...` ID unless `--job-id` is provided. Each workspace owns its crawler result, extraction JSON, checks, screenshots, audit JSON, report, publication package, and manifest; one audit never uses another audit's generated files.

Other generated artifacts are written under `shared/generated/` and are ignored by git:

- `shared/generated/audit-report/`
- `shared/generated/gtm-report/`
- `shared/generated/vercel-gtm-report/`
- `shared/generated/mobile-audits/`
- `shared/generated/screenshot-audits/`
- `shared/generated/figma-audits/`

Figma audit output for a job is usually under:

```text
shared/generated/figma-audits/<job-id>/
```

## Project Structure

```text
figma_audit/                 Figma audit pipeline, checks, evidence, and report builder
scripts/run_pipeline.py      Main website audit pipeline launcher
src/audit/                   Website extraction and check logic
src/figma_audit_runner.py    Figma audit runner used by the UI and CLI
src/gtm_audit/               UX/UI report generation modules
src/mobile_audit/            Android/Appium extraction and mobile report logic
src/report/                  Static detailed report generator
src/ui/                      Local audit launcher server and frontend
shared/audits/<job-id>/      Isolated website-audit workspace and generated evidence
shared/generated/            Other local generated reports and audit artifacts
```

## Persistent jobs and recovery

The UI accepts an audit as a durable queued job, then a bounded local worker claims it, renews a lease while it runs, and writes results to the job workspace. The default single-instance backend is SQLite at `shared/state/jobs.sqlite3` (or `UX_JOB_DATABASE_URL=sqlite:///absolute/path/jobs.sqlite3`). Runtime state is ignored by Git and Docker.

```text
HTTP request -> durable queued job -> worker claim + lease -> isolated audit workspace -> terminal result
```

Useful controls are `UX_AUDIT_WORKER_CONCURRENCY` (default `1`), `UX_AUDIT_MAX_QUEUED` (default `100`), `UX_AUDIT_WORKER_LEASE_SEC` (default `45`), `UX_AUDIT_TOTAL_TIMEOUT_SEC` (default `3600`), `UX_AUDIT_STAGE_TIMEOUT_SEC` (default `900`), `UX_AUDIT_TRANSIENT_STAGE_RETRIES` (default `1`), `UX_PUBLICATION_TIMEOUT_SEC` (default `600`), `UX_AUDIT_MAX_PAGES` (default `50`), `UX_AUDIT_RETENTION_DAYS` (default `30`), and `UX_AUDIT_STORAGE_MAX_BYTES` (default 5 GiB). Only classified connection/browser timeout failures retry, and retries are bounded. Expired worker leases are marked `interrupted`, never automatically rerun. Queued cancellation is immediate; running cancellation terminates the application-owned process tree.

`/health` is a cheap liveness/storage/store check; `/ready` additionally requires a running worker and a detectable Playwright runtime. Both return JSON. Request IDs are returned in `X-Request-ID` and attached to job creation events.

`UX_DEPLOYMENT_MODE=distributed` intentionally fails startup in this release: a local SQLite file cannot coordinate multiple containers. A production multi-instance deployment needs a shared PostgreSQL-capable job backend plus its external database provisioning. Likewise, custom criteria (`AUDIT_CRITERIA_CONFIG_PATH`) and audit workspaces need mounted durable storage on ephemeral platforms if they must survive redeploys.

## Website discovery and coverage

Website audits use deterministic representative page sampling, not a claim of a full-site crawl. Discovery combines homepage navigation, useful footer links, robots-declared or standard sitemaps, and optional public authentication pages. `robots.txt` defaults to `respect` (`UX_AUDIT_ROBOTS_POLICY=respect`); `report_only` records disallowance without silently hiding it. Authentication pages are excluded by default and can only be included with the explicit `UX_AUDIT_INCLUDE_AUTH_PAGES=1` option; no credentials are entered or forms submitted.

The default locale is `auto`: site URLs such as `/fr/products` are preserved. Set `UX_AUDIT_LOCALE` only when a consultant deliberately wants one browser locale. Each run saves a sanitized effective configuration at `input/run_config.json` and a coverage manifest at `coverage/manifest.json`. The manifest distinguishes discovered, selected, completed, failed, and excluded pages; it records page-limit, robots, authentication, duplicate/domain, and collection outcomes. `UX_AUDIT_MIN_COVERAGE_RATIO` (default `0.8`) marks a completed execution as coverage `incomplete` when too few selected pages were collected.

## Git / Push Hygiene

The `.gitignore` excludes local secrets, virtual environments, caches, Playwright artifacts, generated reports, generated screenshots, Figma audit outputs, Vercel local state, and imported archive files.

Ignored rules do not untrack files that were already committed. If git still shows old generated artifacts, remove them from the index once with `git rm --cached <path>` and then commit the updated ignore rules.

Before pushing, check:

```bash
git status --short
git diff -- .gitignore requirements.txt README.md
```

## Reproducible container and verification

```bash
uv sync --frozen
uv run pytest -q
docker build --pull=false -t pfe-uxui-auditor:phase0 .
docker run --rm -p 10000:10000 \
  -e UX_AUTH_SERVICE_URL=http://127.0.0.1:9/api/v1 \
  pfe-uxui-auditor:phase0
```

The health endpoint does not contact external services. The image runs as the unprivileged `auditor` user and pins Playwright 1.43.0 to the matching Playwright base image; Vercel CLI is pinned to 58.0.0. `requirements.txt` is a compatibility export and must remain aligned with the lock.

See [docs/SECURITY_OPERATIONS.md](docs/SECURITY_OPERATIONS.md) for authentication, SSRF, publication, credential rotation/history cleanup, and rollback procedures. The release remains blocked until the repository owner revokes/rotates the exposed tunnel credential and completes the coordinated remote-history purge.
