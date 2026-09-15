# Versioning

**Status:** Current identifier inventory plus clearly marked recommendations
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-15
**Audience:** Maintainers, contributors, and release reviewers
**Scope:** Existing version identifiers and compatibility boundaries; not an adopted release policy.
**Related documents:** [Database Specification](DATABASE-SPECIFICATION.md), [Technical Specification](TECHNICAL-SPECIFICATION.md), [Release Plan](RELEASE-PLAN.md), [Decisions](DECISIONS.md).

## Current state

No formal application release-versioning policy, release-tag convention, or SemVer adoption is established by the repository. Git commit hashes and branches identify repository states; documentation-only commits are not application releases.

## Current identifiers

- Python project metadata: `pfe-ux-ui-auditor` version `0.1.0` in `pyproject.toml`.
- Frontend package metadata: `ux-ui-auditor-pipeline` version `1.0.0` in `package.json`.
- SQLite schema: version 3, with ordered `JobStore` migrations.
- API: no URL-version prefix or published OpenAPI version.
- Container builds use explicit local image tags; CI uses `ux-ui-auditor-ci`.
- Prompt/model settings may carry configuration values, but they are not a project release-version system.

Application version, Git commit, and SQLite schema version are separate identifiers. Schema migration compatibility follows the implementation; do not infer an application release version from schema version. Frontend and backend are built and served together in this repository.

## Documentation baseline

The implementation baseline records the application state against which documentation was verified. A newer documentation commit/head must not be presented as a newer application release.

## Recommended / not currently adopted

A future owner may adopt `MAJOR.MINOR.PATCH` with documented compatibility, tag, and release-note rules. This is a recommendation only, not current project practice.
