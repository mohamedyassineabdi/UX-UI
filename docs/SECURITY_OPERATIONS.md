# Security operations and release gate

## Legacy credential incident

The old tunnel credential must be treated as compromised. The repository owner must confirm that it has been revoked or rotated in the provider dashboard and that every local tunnel configuration using it has been disabled or updated. Never paste the old or replacement value into tickets, chat, CI logs, commands, test fixtures, or documentation.

The legacy incident path, `UX-UI_-Agent/info .txt`, is not present in the reachable history of this `UX-UI` repository. Do not run `git filter-repo`, rewrite this repository's history, or force-push merely because of the legacy incident. The full-history Gitleaks CI gate protects the current repository.

If a future scan finds the legacy credential in this repository, stop normal releases and coordinate any history rewrite on a disposable mirror with the repository owner and branch-protection administrators. Do not perform that rewrite from a normal working clone.

## Rollback

For an application rollback, redeploy the last known-good image digest while retaining the authentication and network controls. Do not restore the raw HTML publication endpoint or any legacy credential file. If a future coordinated history rewrite fails review, discard the disposable rewrite, leave the protected remote unchanged, correct the filter procedure, and repeat.

## Security model

- `/health` and launcher assets are public; API, audit, report, artifact, upload, cancel, criteria, and publication routes require a portal bearer token.
- Normal users can access only their own audit identifiers. Administrators additionally mutate/reset criteria; they do not implicitly inherit another user's reports.
- URLs are limited to public HTTP(S) destinations on configured ports. DNS answers, redirects, discovered URLs, and browser requests are checked; Chromium is DNS-pinned and service workers are blocked.
- TLS validation is on by default. The development override is rejected in production and emits a visible warning locally.
- Publication deploys an isolated temporary copy of the selected immutable machine report. Local edits are not accepted as HTML and are not published in Phase 0.

## CSRF classification

CSRF protection is not applicable to the Phase 0 mutation API: sensitive endpoints authenticate only through an explicitly supplied `Authorization: Bearer` token. The server does not use ambient browser cookies for authorization. If cookie-backed authentication is introduced later, mutation endpoints must add CSRF protection before release.

## Infrastructure boundary

This repository contains application, Docker, Nginx, and VPS deployment configuration; it does not contain AWS ALB listener or routing configuration. Application bearer authentication does not prove ALB protection. The infrastructure owner must verify ALB protections in AWS before an internet-facing release that uses an ALB.

## Persistent criteria configuration

Custom audit criteria are written atomically to `AUDIT_CRITERIA_CONFIG_PATH`; when unset, the application uses `shared/config/audit_axes.json`. Docker, Render, and other ephemeral container deployments must mount or otherwise provide durable storage at the configured path if custom criteria must survive a redeploy. The repository cannot provide that external persistent volume itself.
