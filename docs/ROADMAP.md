# Roadmap

**Status:** Decision-oriented; no dates or approvals inferred
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** Product, engineering, and delivery stakeholders
**Scope:** Current decisions and candidate work, linked to the [Implementation Plan](IMPLEMENTATION-PLAN.md).
**Related documents:** [Implementation Plan](IMPLEMENTATION-PLAN.md), [Checkpoint](CHECKPOINT.md), [Security Operations](SECURITY_OPERATIONS.md).

| Status | Item | Link / decision need |
| --- | --- | --- |
| Current baseline | Evidence/provenance, measurement, scoring, review workflow, and frontend bundling are implemented | [Implementation Plan](IMPLEMENTATION-PLAN.md#current-baseline) |
| Blocked | Release prerequisite: owner confirmation that inherited credential remediation is complete | [Security Operations](SECURITY_OPERATIONS.md) |
| Candidate next - confirmation required | Shared store/artifacts for distributed deployment | [Conditional phase](IMPLEMENTATION-PLAN.md#distributed-deployment) |
| Conditional | Enable hosted screenshot/mobile only with compatible runtime and verification | [Conditional phase](IMPLEMENTATION-PLAN.md#hosted-screenshot-and-mobile-operation) |
| Proposed | Score calibration and reviewer validation | [Proposed phase](IMPLEMENTATION-PLAN.md#score-calibration-and-reviewer-validation) |

The repository does not establish management approval, delivery dates, or an obligation to distribute the application. Current technical debt remains: local SQLite is single-instance, static screenshots do not establish hidden runtime behavior, and score calibration is not an approved benchmark.
