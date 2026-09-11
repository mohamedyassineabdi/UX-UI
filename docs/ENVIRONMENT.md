# Environment

**Status:** Current committed local/runtime prerequisites
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b` (the application implementation baseline; current documentation integration is `bfb3c95`)
**Last updated:** 2026-09-11
**Audience:** Developers and operators
**Scope:** Runtime prerequisites and safe local setup; variable reference is in [Configuration](CONFIGURATION.md).
**Related documents:** [README](../README.md), [Deployment](DEPLOYMENT.md), [Testing](TESTING.md).

## Prerequisites

Use Python `>=3.10,<3.13` and the locked `uv` environment. Node.js 20+ is required for the bundled React/Vite frontend and tooling. Website audits require the Playwright browser runtime; Docker supplies the matching Playwright image. Mobile audits additionally require a trusted local Appium endpoint, compatible Android emulator/device, and Android tooling. Figma, model review, portal authentication, and Vercel publication require their respective external credentials/services.

## Local setup

Run `uv sync --frozen`, then `npm ci --ignore-scripts` and `npm run build`. Start the application with `uv run python -m src.ui.server`; by default it listens at `0.0.0.0:8787`. Create a git-ignored `.env` only for local values; `deploy/ux-ui-auditor.env.example` is a safe server-oriented example, not a complete production configuration.

Outside local development, configure `UX_AUTH_SERVICE_URL`. Development bypass is intentionally limited to loopback binding and must never be enabled in staging/production. The local store/artifacts are not shared infrastructure; do not point multiple application instances at them.

For exact test/build commands see [Testing](TESTING.md). Docker is optional for local development but required to reproduce the CI image gate.
