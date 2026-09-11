# Testing

**Status:** Current committed validation guidance
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Contributors, maintainers, and CI reviewers
**Scope:** Existing automated checks and how to select them; it does not claim coverage percentages.
**Related documents:** [Technical Specification](TECHNICAL-SPECIFICATION.md), [Security](SECURITY.md), [Deployment](DEPLOYMENT.md), [Checkpoint](CHECKPOINT.md).

## Canonical commands

```powershell
uv sync --frozen
npm ci --ignore-scripts
npm run build
uv run python -m compileall src figma_audit navigator scripts
uv run pytest -q
```

CI runs those build/test/compile checks on Python 3.12, verifies no framework CDN references in the production bundle, performs a full-history Gitleaks scan, and builds the Docker image. The repository has no configured lint, formatter, type-checker, browser E2E framework, or coverage threshold; do not describe one as required.

## Suite map

| Area | Current tests |
| --- | --- |
| Workspace, isolation, discovery/coverage | `test_audit_workspace.py`, `test_discovery_scope.py`, `test_website_pipeline_isolation.py` |
| Jobs/store/migrations | `test_job_queue.py` |
| Auth, API/server, upload, network | `test_auth.py`, `test_auth_integration.py`, `test_server_security.py`, `test_upload_security.py`, `test_network_policy.py` |
| Frontend/publication security | `test_frontend_security.py`, `test_publication_security.py` |
| Result semantics/scoring/measurement | `test_phase2b_semantics.py`, `test_phase3a_scoring.py`, `test_phase3b_measurement.py` |
| Tool-backed checks | `test_axe_runner.py`, `test_lighthouse_runner.py` |
| Review UI/workflow | `test_review_workflow.py`, `test_review_ui_contract.py` |
| Dependency consistency | `test_dependency_consistency.py` |

Fixtures are under `tests/fixtures/`; tests use temporary paths, mocks, and local loopback services where appropriate. `test_auth_integration.py` is a loopback contract smoke test, not a call to a production portal.

## Minimum validation by change

| Change | Minimum checks |
| --- | --- |
| Python/server/jobs | full pytest, compileall, affected job/API tests |
| Frontend | npm install/build, frontend security/contract tests, relevant API tests |
| Database/review | job queue and review workflow tests |
| Security/input handling | auth, network policy, server, upload, frontend, publication security tests |
| Scoring/measurement | Phase 2B, Phase 3A/3B, Axe, Lighthouse tests |
| Docker/deployment | build image when Docker daemon is available; inspect CI/Render configuration |
| Documentation | link/anchor/path checks and `git diff --check` |

## External and environment-dependent checks

Browser binaries, target websites, Figma, model providers, Appium/ADB, portal auth, Vercel, and Docker are dependencies outside the deterministic unit/contract suite. Record unavailable dependencies as **NOT VERIFIED**, not passed. The Windows OpenSSL abort seen in the Phase 1 checkpoint is local-environment evidence only; retry `test_auth_integration.py` on the current target environment rather than treating it as a universal test failure.

Place tests beside their existing concern with `test_*.py` names, use temporary resources rather than repository outputs, and update the engineering contract/documentation with behavior changes.
