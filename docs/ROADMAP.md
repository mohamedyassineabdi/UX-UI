# Roadmap

**Status:** Decision-oriented; no dates or approvals inferred
**Repository baseline:** `main @ 5d9646c4daa221f43c82cd8d477144900193bdb0`
**Last updated:** 2026-09-10
**Audience:** Product, engineering, and delivery stakeholders
**Scope:** Current decisions and candidate work, linked to the [Implementation Plan](IMPLEMENTATION-PLAN.md).
**Related documents:** [Implementation Plan](IMPLEMENTATION-PLAN.md), [Checkpoint](CHECKPOINT.md), [Security Operations](SECURITY_OPERATIONS.md).

| Status | Item | Link / decision need |
| --- | --- | --- |
| In progress | Commit/validate richer evidence and provenance work | [In-progress phase](IMPLEMENTATION-PLAN.md#rich-evidence-and-provenance-semantics) |
| Blocked | Release prerequisite: owner confirmation that inherited credential remediation is complete | [Security Operations](SECURITY_OPERATIONS.md) |
| Candidate next - confirmation required | Shared store/artifacts for distributed deployment | [Conditional phase](IMPLEMENTATION-PLAN.md#distributed-deployment) |
| Conditional | Enable hosted screenshot/mobile only with compatible runtime and verification | [Conditional phase](IMPLEMENTATION-PLAN.md#hosted-screenshot-and-mobile-operation) |
| Proposed | Score calibration and reviewer validation | [Proposed phase](IMPLEMENTATION-PLAN.md#score-calibration-and-reviewer-validation) |

The repository does not establish management approval, delivery dates, or an obligation to distribute the application. Current technical debt remains: local SQLite is single-instance, static screenshots do not establish hidden runtime behavior, and in-progress richer result semantics are not baseline contracts.
