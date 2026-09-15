# Bug Triage

**Status:** Recommended defect-classification and closure guidance
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-15
**Audience:** Contributors, maintainers, reviewers, and release stakeholders
**Scope:** Defects specifically; broader changes remain in [Issue and Change Management](ISSUE-AND-CHANGE-MANAGEMENT.md).
**Related documents:** [Issue Template](ISSUE-TEMPLATE.md), [Testing](TESTING.md), [Security Operations](SECURITY_OPERATIONS.md), [Release Process](RELEASE-PROCESS.md).

## What qualifies as a bug

A bug is a reproducible difference between implemented/contracted behavior and observed behavior. A feature request, unresolved product decision, UX recommendation, environment limitation, external-provider failure, or documentation defect is not automatically an implementation bug.

## Triage inputs

Capture reproducibility, user/security impact, data integrity, availability, audit/report correctness, workaround availability, and affected scope. Record environment, commit, audit mode/input category, safe logs/request/job IDs, expected/actual result, and a minimal reproducer or regression test where practical.

## Recommended severity classification

| Severity | Meaning |
| --- | --- |
| Critical | Potential security compromise, data exposure/destructive corruption, or system-wide unusability. |
| High | Core supported workflow unusable or materially incorrect without a reasonable workaround. |
| Medium | Significant limited-scope defect or a defect with workaround. |
| Low | Minor functional or visual defect with limited impact. |

Severity and priority differ: priority also depends on frequency, release relevance, security, dependencies, and available workaround. No response-time SLA is established.

## Special classes and escalation

Security issues follow [Security Operations](SECURITY_OPERATIONS.md). Scoring/measurement correctness, API/schema regressions, frontend defects, provider failures, and deployment/environment failures require their relevant contract and test evidence. Escalate significant architecture changes through [Decisions](DECISIONS.md); use [Release Process](RELEASE-PROCESS.md) for release impact.

## Resolution evidence

Do not mark a bug resolved merely because code changed. Require regression/affected tests, documentation updates where behavior changed, build/security evidence, and external verification when the defect depends on external systems. Recommended states are New, Confirmed, Needs evidence, In progress, Blocked, Resolved, and Not a bug; no ticketing platform is implied.
