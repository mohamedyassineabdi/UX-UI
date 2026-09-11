# Configuration

**Status:** Current committed application configuration reference
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b` (the application implementation baseline; current documentation integration is `bfb3c95`)
**Last updated:** 2026-09-11
**Audience:** Developers and operators
**Scope:** Application-controlled environment variables and checked-in configuration files; credentials are names only.
**Related documents:** [Environment](ENVIRONMENT.md), [Deployment](DEPLOYMENT.md), [Security](SECURITY.md), [Technical Specification](TECHNICAL-SPECIFICATION.md).

## Configuration sources

The application reads environment variables directly in Python/Node-adjacent source. `shared/config/audit_axes.json` is the default criteria/axis configuration; `AUDIT_CRITERIA_CONFIG_PATH` can select another criteria file. `vite.config.mjs` controls the frontend build, and `src/ui/frontend` reads a runtime API base URL through the generated/static configuration contract. `deploy/ux-ui-auditor.env.example` is a safe partial example. Values are parsed at startup or call time as the owning module implements; invalid numeric/enum values generally cause a request/startup error rather than silent coercion.

## Variable reference

| Variables | Purpose / default or constraint | Sensitive |
| --- | --- | --- |
| `HOST`, `PORT`, `APP_ENV`, `UX_ENVIRONMENT`, `UX_LOG_LEVEL` | Listener defaults to `0.0.0.0:8787`; environment controls auth/Figma safety; log default `INFO` | no |
| `UX_AUTH_SERVICE_URL`, `UX_DEV_AUTH_BYPASS`, `UX_AUTH_CONNECT_TIMEOUT_SECONDS`, `UX_AUTH_READ_TIMEOUT_SECONDS` | Portal auth endpoint; bypass is loopback development only; timeouts default 2/5 seconds | no |
| `UX_CORS_ALLOWED_ORIGINS`, `UX_RATE_LIMIT_PER_MINUTE`, `UX_AUDIT_CREATE_RATE_LIMIT_PER_MINUTE` | Browser-origin and request/create rate limits; defaults localhost origins, 120, and 5 | no |
| `UX_MAX_JSON_BODY_BYTES`, `UX_MAX_MULTIPART_BODY_BYTES`, `UX_MAX_UPLOAD_COUNT`, `UX_MAX_UPLOAD_BYTES`, `UX_MAX_IMAGE_DIMENSION`, `UX_MAX_IMAGE_PIXELS` | Positive upload/body/image limits; defaults 1 MiB, 25 MiB, 10, 8 MiB, 8000, 40M pixels | no |
| `UX_JOB_DATABASE_URL`, `UX_DEPLOYMENT_MODE`, `UX_AUDIT_WORKER_CONCURRENCY`, `UX_AUDIT_WORKER_LEASE_SEC` | SQLite URL only; mode `local`/`single-instance` accepted, distributed rejected; worker defaults 1/45 seconds | no |
| `UX_AUDIT_MAX_QUEUED`, `UX_AUDIT_RETENTION_DAYS`, `UX_AUDIT_STORAGE_MAX_BYTES` | Queue/retention/storage controls | no |
| `UX_AUDIT_STAGE_TIMEOUT_SEC`, `UX_AUDIT_STAGE_TIMEOUT_<STAGE>_SEC`, `UX_AUDIT_TOTAL_TIMEOUT_SEC`, `UX_AUDIT_TRANSIENT_STAGE_RETRIES` | Stage default 900 s, total 3600 s, retry default 1 | no |
| `UX_ALLOWED_OUTBOUND_PORTS`, `UX_DNS_TIMEOUT_SECONDS` | SSRF outbound ports (default `80,443`) and DNS timeout (default 3 s) | no |
| `UX_AUDIT_LOCALE`, `UX_AUDIT_MAX_PAGES`, `UX_AUDIT_MIN_COVERAGE_RATIO`, `UX_AUDIT_ALLOWED_DISCOVERY_HOSTS`, `UX_AUDIT_INCLUDE_AUTH_PAGES`, `UX_AUDIT_ROBOTS_POLICY` | Collection locale/page/coverage/discovery/robots behavior; defaults include `auto`, 50, .8, and `respect` | no |
| `UX_SITEMAP_MAX_FILES`, `UX_SITEMAP_MAX_URLS`, `UX_SITEMAP_MAX_BYTES`, `UX_SITEMAP_MAX_DEPTH`, `UX_LIGHTHOUSE_TIMEOUT_SEC` | Sitemap/Lighthouse bounds | no |
| `AUDIT_BROWSER_HEADLESS`, `AUDIT_BROWSER_TYPE`, `AUDIT_BROWSER_CHANNEL`, `AUDIT_BROWSER_IGNORE_HTTPS_ERRORS`, `AUDIT_BROWSER_SLOW_MO_MS`, `AUDIT_BROWSER_VIEWPORT_WIDTH`, `AUDIT_BROWSER_VIEWPORT_HEIGHT`, `AUDIT_PAGE_CONCURRENCY` | Playwright/browser execution configuration | no |
| `AUDIT_WORKBOOK_TEMPLATE`, `AUDIT_CRITERIA_CONFIG_PATH`, `AUDIT_CONFIG`, `AUDIT_MAX_SAFE_INTERACTIONS_PER_PAGE`, `AUDIT_RESPONSIVE_CHECK_ENABLED`, `AUDIT_RESPONSIVE_MOBILE_WIDTH`, `AUDIT_RESPONSIVE_MOBILE_HEIGHT`, `AUDIT_PARTS_OUTPUT_DIR`, `AUDIT_SCORE_MODEL__*` | Workbook, criteria, audit/check/output settings; `AUDIT_SCORE_MODEL__*` is a nested configuration prefix | no |
| `SCREENSHOT_AUDITS_DISABLED`, `SCREENSHOT_AUDIT_LLM_REFINEMENT`, `FIGMA_AUDITS_DISABLED`, `MOBILE_AUDITS_DISABLED` | Deployment feature gates; Render disables screenshot/mobile | no |
| `FIGMA_TOKEN`, `FIGMA_TOKENS`, `FIGMA_API_BASE`, `FIGMA_CA_BUNDLE`, `FIGMA_VERIFY_SSL`, `FIGMA_TRUST_ENV_PROXY`, `FIGMA_AUDIT_CRITERIA_PATH`, `FIGMA_FETCH_VARIABLES`, `FIGMA_FILE_REGEX`, `FIGMA_RENDER_TYPES`, `FIGMA_IMAGE_REQUEST_TIMEOUT`, `FIGMA_IMAGE_MAX_RETRIES`, `FIGMA_MAX_RETRY_SLEEP_SECONDS`, `FIGMA_MAX_RETRY_AFTER_SECONDS`, `FIGMA_RATE_LIMIT_RETRIES`, `FIGMA_MIN_REQUEST_INTERVAL_SECONDS` | Figma auth, transport, criteria, fetch/rate-limit behavior | tokens sensitive |
| `REQUEST_TIMEOUT`, `MAX_RETRIES`, `RETRY_BACKOFF_SECONDS`, `ANNOTATION_IMAGE_SCALE`, `ANNOTATION_MAX_IMAGES`, `ANNOTATION_WORKERS`, `DETECTION_MAX_ISSUES_PER_CHECK`, `DETECTION_WORKERS`, `MAX_RUNTIME_SECONDS` | Figma CLI/request/annotation/detection limits | no |
| `APPIUM_SERVER_URL`, `MOBILE_AUDIT_ADB_PATH`, `MOBILE_AUDIT_ANDROID_SDK_ROOT`, `ANDROID_HOME`, `ANDROID_SDK_ROOT` | Local Appium/ADB/Android resolution | no |
| `MOBILE_VISION_SCREEN_LIMIT`, `MOBILE_LIVE_SKIP_VISION`, `MOBILE_LIVE_SKIP_LLM`, `MOBILE_LIVE_SKIP_TEXT_REFINEMENT` | Live-mobile visual/model controls | no |
| `AI_REVIEW_ENABLED`, `AI_REVIEW_BACKEND`, `AI_REVIEW_BASE_URL`, `AI_REVIEW_MODEL`, `AI_REVIEW_API_KEY`, `AI_REVIEW_TIMEOUT`, `AI_REVIEW_MAX_RETRIES`, `AI_REVIEW_RETRY_BASE_DELAY`, `AI_REVIEW_RETRY_MAX_DELAY`, `AI_REVIEW_REQUEST_SPACING_SECONDS`, `AI_REVIEW_PROMPT_VERSION` | Optional review-provider behavior | API key sensitive |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`; `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`; `OLLAMA_API_KEY`, `OLLAMA_API_HOST`, `OLLAMA_BASE_URL`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_VISION_MODEL`, `OLLAMA_REPORT_MODEL`, `OLLAMA_AI_REVIEW_MODEL`, `OLLAMA_REQUEST_TIMEOUT`, `OLLAMA_REPORT_POLISH`, `OLLAMA_AI_REVIEW` | Provider credentials/endpoints/models; several are compatibility/fallback inputs in model clients | keys sensitive |
| `GTM_SKIP_VISION`, `GTM_SKIP_LLM`, `GTM_HEURISTIC_SPOTLIGHTS`, `GTM_VISION_BASE_URL`, `GTM_VISION_MODEL`, `GTM_VISION_API_KEY`, `GTM_VISION_MAX_SCREENSHOTS`, `GTM_VISION_SCREEN_LIMIT`, `GTM_VISION_PROMPT_VERSION`, `GTM_VISION_VERIFY_SPOTLIGHTS` | GTM visual/model enrichment | API key sensitive |
| `CRAWLER_USE_AI_NAV`, `USE_AI_NAV`, `CRAWLER_VERIFY_AUTH_PATHS`, `CRAWLER_AUTH_TIMEOUT_SEC` | Optional crawler AI/auth-path behavior | no |
| `GTM_AUTO_DEPLOY`, `GTM_DISABLE_VERCEL_DEPLOY`, `GTM_REPORT_DIR`, `GTM_VERCEL_DIR`, `UX_PUBLICATION_TIMEOUT_SEC`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `VERCEL_SCOPE` | Optional Vercel publication and local report paths; publication timeout default 600 s | Vercel token sensitive |
| `NODE_BINARY`, `UX_UI_AUDITOR_API_BASE_URL`, `UX_UI_AUDITOR_CONFIG__*` | Lighthouse Node executable; frontend runtime API base and nested runtime configuration prefix | no |

`LOCALAPPDATA` and `USERPROFILE` are read only as platform fallbacks for Android SDK discovery, not application configuration. `OLLAMA_HOST`/`OLLAMA_BASE_URL` and the mobile `GTM_*` fallbacks are compatibility aliases, not a guarantee that every provider mode is enabled.

## Safe example

```dotenv
HOST=127.0.0.1
PORT=8787
UX_AUTH_SERVICE_URL=http://127.0.0.1:8000/api/v1
AUDIT_BROWSER_HEADLESS=1
UX_AUDIT_ROBOTS_POLICY=respect
```

Keep real tokens in the deployment secret store or a git-ignored environment file. Do not add a `.env` with values to the repository.
