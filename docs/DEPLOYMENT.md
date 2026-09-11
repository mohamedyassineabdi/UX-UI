# Deployment

**Status:** Current committed deployment contract
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b` (the application implementation baseline; current documentation integration is `bfb3c95`)
**Last updated:** 2026-09-11
**Audience:** Operators and release engineers
**Scope:** Docker, Render, and optional report publication; environment variable detail is in [Configuration](CONFIGURATION.md).
**Related documents:** [Technical Specification](TECHNICAL-SPECIFICATION.md), [Environment](ENVIRONMENT.md), [Security](SECURITY.md), [Security Operations](SECURITY_OPERATIONS.md).

## Supported model

The supported runtime is one Python application instance with local worker threads, subprocesses, SQLite, and local workspaces. `UX_DEPLOYMENT_MODE=distributed` intentionally fails; a shared job/artifact design is not implemented. Ephemeral platforms need externally supplied durable storage for retained artifacts and custom criteria.

## Build and container

`Dockerfile` uses a digest-pinned Node 20.20.2 builder and digest-pinned Playwright Python 1.43 image. It installs locked Python dependencies with `uv sync --frozen --no-dev --no-install-project`, runs `npm ci --omit=optional --ignore-scripts`, installs Vercel CLI 58.0.0, copies the source, and runs `npm run build`. Vite emits `src/ui/static/app/`; Python serves it. The runtime user is non-root `auditor`, port `10000` is exposed, and `/health` is the configured healthcheck.

Build with `docker build --pull=false -t ux-ui-auditor-phase2-docs .` when a Docker daemon is available. CI additionally inspects the image user/healthcheck and verifies the bundle has no framework CDN URLs.

## Render and operational behavior

`render.yaml` deploys Docker with `/health`, binds port 10000, and enables headless Chromium with page concurrency 2. Its supplied values disable screenshot and mobile jobs, disable vision/refinement paths, and leave Figma enabled unless `FIGMA_AUDITS_DISABLED` is separately set. Render supplies an OpenAI key by secret synchronization; never place a value in repository configuration.

The server starts from `python -m src.ui.server`. `/health` checks liveness/storage/job store; `/ready` additionally requires a healthy worker and browser availability. Audit reports may be published through the optional Vercel CLI path only when its required credentials/configuration are provided.

Backup, persistent volumes, multi-instance orchestration, external auth operation, provider uptime, and Vercel project administration are external responsibilities. See [Security Operations](SECURITY_OPERATIONS.md) for release prerequisites.
