# Release Process

**Status:** Recommended release-gate process based on current repository evidence
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Maintainers, operators, and release reviewers
**Scope:** Project-level preparation and decision gates; technical deployment is documented separately.
**Related documents:** [Deployment](DEPLOYMENT.md), [Security Operations](SECURITY_OPERATIONS.md), [Quality Gates](QUALITY-GATES.md), [Checkpoint](CHECKPOINT.md).

## Scope and pre-release requirements

Establish intended release scope, then retain evidence for locked dependencies, frontend build, Python compilation, deterministic and affected feature/security tests, documentation consistency, and secret scanning. Docker image validation is conditional on an available daemon or CI-capable environment. Unavailable external checks must remain **NOT VERIFIED**.

## Security prerequisites

Authentication/ownership behavior, URL/upload/network protections, and secret scanning are current repository gates. The inherited credential remediation requires owner confirmation before a normal release; repository scanning does not establish external revocation or rotation.

## Release decision and integration

Repository evidence can establish implemented checks, not business approval or production readiness. A release reviewer/product authority must supply any required confirmation outside the repository. Fetch first, verify the target branch and clean scope, use review/PR where available, integrate non-force only, and never overwrite newer remote work.

## Deployment and publication

Deployment follows [Deployment](DEPLOYMENT.md). Application release is distinct from owner-scoped audit report publication: publication creates an immutable selected snapshot and may rely on optional external Vercel configuration. Neither action proves post-release monitoring or external provider availability.

## Rollback and post-release verification

Use the documented deployment rollback approach and retain authentication/network protections. Where a deployment exists, verify health/readiness and relevant secured smoke checks. The repository does not establish production monitoring, a release schedule, or a rollback service-level objective.
