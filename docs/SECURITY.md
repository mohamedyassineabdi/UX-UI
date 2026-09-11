# Security

**Status:** Current committed security architecture
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b` (the application implementation baseline; current documentation integration is `bfb3c95`)
**Last updated:** 2026-09-11
**Audience:** Engineers, security reviewers, and operators
**Scope:** Application controls; release procedures and the inherited credential prerequisite are in [Security Operations](SECURITY_OPERATIONS.md).
**Related documents:** [API Specification](API-SPECIFICATION.md), [Security Operations](SECURITY_OPERATIONS.md), [Deployment](DEPLOYMENT.md), [Configuration](CONFIGURATION.md).

## Trust boundaries and objectives

The server protects portal-authenticated users, owner-scoped jobs and artifacts, local filesystem workspaces, target-site requests, Figma/model providers, Appium/device access, and optional Vercel publication. Target websites, provider responses, browser content, and external infrastructure are untrusted inputs.

## Authentication and authorization

Protected API requests require `Authorization: Bearer <token>`. `src/security/auth.py` validates the token against the portal `/auth/me` endpoint, fails closed on invalid/network/upstream failures, and accepts only active `user` or `admin` identities. `UX_DEV_AUTH_BYPASS` is allowed only for a loopback development listener and is forbidden in production/staging. Owner checks cover jobs, reports, artifacts, reviews, cancellation, and publication; non-owners receive `404`. Criteria writes/resets require `admin`.

## Input, network, and browser controls

Website URLs must be public HTTP(S), credential-free, DNS-resolvable to public addresses, and on `UX_ALLOWED_OUTBOUND_PORTS` (default 80/443). Validation rejects local/private/reserved addresses, localhost, malformed/ambiguous numeric hosts, unsupported ports, and unsafe redirects. DNS-pinned HTTP fetching revalidates redirects; Playwright receives DNS pinning and request routing that blocks destinations outside approved public addresses. TLS is used for HTTPS connections. Safe interaction is default-deny: the product blocks account/auth flows, downloads, external/custom-scheme navigation, forms, and state-changing actions; see [ADR-005](DECISIONS.md#adr-005-default-deny-interactions).

Screenshot uploads have request, count, byte, MIME/image-decode, dimension, and pixel limits. Workspace/job IDs and artifact paths are validated/contained; static and artifact retrieval resolves paths under approved roots and rejects symlink escape. Workspace writes use atomic same-directory temporary files.

## HTTP and frontend controls

The server sends a CSP constrained to self plus configured connection sources, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and route-specific CORS. The built React/Vite bundle is served locally; production CI checks it does not reference framework CDNs. The repository does not implement cookie-session CSRF protection because the authenticated contract is bearer-header based; CORS origin allowlisting remains relevant for browser callers.

## Review, publication, and secrets

Review revisions are append-only and publication creates immutable snapshots. Reviewed publication requires a validated/approved revision; a separate machine-unreviewed path exists. The publication endpoint does not accept arbitrary edited report HTML. Tokens and provider credentials are environment variables only; documentation and examples list names, never values. CI runs a full-history Gitleaks scanning gate using `.gitleaks.toml`.

## Supply chain and residual risk

Python and Node dependencies are locked in `uv.lock` and `package-lock.json`; Docker pins its Node and Playwright base images by digest and runs as non-root `auditor`. CI builds the frontend, runs tests/compile checks, scans history, and builds the image.

| Threat | Implemented control | Residual risk |
| --- | --- | --- |
| Stolen/invalid bearer | Portal `/auth/me`, fail-closed validation | Availability/trust of external auth service |
| SSRF/DNS rebinding | public-IP validation, DNS pinning, redirects/browser guards | Target sites and browser engines remain external dependencies |
| Cross-user disclosure | owner checks and contained artifact paths | Local SQLite/files require host access control |
| Malicious upload/path | size/image validation, job/path containment, atomic writes | Image parsing/browser tooling are dependencies |
| Unsupported AI assertion | evidence/provenance semantics and review | Model output is probabilistic |
| Secret exposure | ignored env files and full-history secret scan | External remediation of inherited credentials remains required |

Known constraints include single-instance local persistence, external auth/provider/deployment trust, and the release prerequisite recorded in [Security Operations](SECURITY_OPERATIONS.md).
