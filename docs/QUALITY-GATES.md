# Quality Gates

**Status:** Current evidence inventory plus recommended release gates
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Contributors, maintainers, and release reviewers
**Scope:** Validation categories and evidence; no unsupported blocking policy is imposed.
**Related documents:** [Testing](TESTING.md), [Release Process](RELEASE-PROCESS.md), [Security](SECURITY.md), [Checkpoint](CHECKPOINT.md).

| Gate | Required evidence | Applies to | Blocking classification | Source |
| --- | --- | --- | --- | --- |
| Locked dependencies | `uv sync --frozen`, `npm ci --ignore-scripts` | Python/frontend changes | Current repository/CI validation | [Testing](TESTING.md) |
| Frontend build | `npm run build` and production-bundle CDN check | Frontend/build changes | Current repository/CI validation | [Testing](TESTING.md) |
| Python compilation | `compileall src figma_audit navigator scripts` | Python changes | Current repository/CI validation | [Testing](TESTING.md) |
| Deterministic and affected tests | Full suite where available plus focused suites | Behavior changes | Current validation expectation | [Testing](TESTING.md) |
| Security tests and secret scan | Relevant auth/network/server/upload/publication tests; full-history scan | Trust-boundary changes | Current repository/CI validation | [Security](SECURITY.md) |
| API/database contract checks | Relevant server/job/review/migration tests | API or persistence changes | Conditional by change scope | [API Specification](API-SPECIFICATION.md) |
| Documentation consistency | Links, anchors, metadata, paths, `git diff --check` | Documentation changes | Current documentation validation | [Contributing](../CONTRIBUTING.md) |
| Docker image build | Repository-supported image build | Container/deployment changes | Conditional: daemon/CI availability | [Deployment](DEPLOYMENT.md) |
| Product/UX and accessibility review | Explicit reviewer confirmation | User-facing interpretation/compliance claims | Manual / confirmation required | [UX Specification](UX-SPECIFICATION.md) |
| Score calibration | Reviewer-agreement evidence and approval | Score/KPI interpretation | Proposed gate | [Implementation Plan](IMPLEMENTATION-PLAN.md#score-calibration-and-reviewer-validation) |
| External integrations | Target-environment evidence for auth, browser, provider, device, or publication | Dependent changes/releases | External verification | [Testing](TESTING.md) |

## Current local limitation

`tests/test_auth_integration.py` is **NOT VERIFIED** on the documented Windows environment because an OpenSSL abort prevents a result. This does not reclassify CI or target-environment expectations. Docker is likewise **NOT VERIFIED** locally when its daemon is unavailable.
