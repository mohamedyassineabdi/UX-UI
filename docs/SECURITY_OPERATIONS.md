# Security operations and release gate

## Credential incident procedure

The removed local tunnel credential must be treated as compromised. The repository owner must:

1. Revoke the exposed ngrok credential in the provider dashboard and issue a replacement only if the tunnel is still needed.
2. Delete or invalidate every local/ngrok agent configuration that used it, stop related tunnels, and verify the old credential can no longer authenticate.
3. Coordinate a protected maintenance window for history cleanup. Use `git filter-repo` on a disposable mirror clone to remove `UX-UI_-Agent/info .txt` from every ref, inspect the rewritten clone, and run a redacted full-history secret scan there.
4. After review, temporarily permit the designated maintainer to perform the required protected force-push. Do not run this from a normal working clone and do not bypass branch protections informally.
5. Restore protections immediately. Require every collaborator and deployment workspace to delete its old clone and reclone; old objects must not be merged or pushed back.

Validation rehearsal (disposable clone only):

```bash
git clone --mirror <repository-url> phase0-purge-test.git
cd phase0-purge-test.git
git for-each-ref --format='%(refname)'
git filter-repo --path "UX-UI_-Agent/info .txt" --invert-paths --force
git rev-list --objects --all | grep -F "UX-UI_-Agent/info .txt" # must print nothing
gitleaks git . --redact --no-banner
```

Inventory nonstandard ref namespaces before the rewrite. The local rehearsal found a Codex-only capture ref that was not rewritten automatically; disposable internal refs must be removed, while any genuine remote ref must be included in the coordinated rewrite rather than silently dropped.

Never paste the old or replacement value into tickets, chat, CI logs, commands, test fixtures, or documentation.

## Rollback

For an application rollback, redeploy the last known-good image digest while retaining the authentication and network controls. Do not restore the raw HTML publication endpoint or the removed credential file. If the history rewrite fails review, discard the disposable rewrite, leave the protected remote unchanged, correct the filter procedure, and repeat. If a coordinated force-push has already happened, use the pre-recorded remote commit ID to perform a second coordinated rewrite; never merge an old clone.

## Security model

- `/health` and launcher assets are public; API, audit, report, artifact, upload, cancel, criteria, and publication routes require a portal bearer token.
- Normal users can access only their own audit identifiers. Administrators additionally mutate/reset criteria; they do not implicitly inherit another user's reports.
- URLs are limited to public HTTP(S) destinations on configured ports. DNS answers, redirects, discovered URLs, and browser requests are checked; Chromium is DNS-pinned and service workers are blocked.
- TLS validation is on by default. The development override is rejected in production and emits a visible warning locally.
- Publication deploys an isolated temporary copy of the selected immutable machine report. Local edits are not accepted as HTML and are not published in Phase 0.
