# Delivery Process

**Status:** Recommended governance process grounded in current validation practice
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Contributors, reviewers, maintainers, and product/UX stakeholders
**Scope:** How changes should move to verified delivery; not evidence of a formally adopted workflow.
**Related documents:** [Contributing](../CONTRIBUTING.md), [Testing](TESTING.md), [Quality Gates](QUALITY-GATES.md), [Issue and Change Management](ISSUE-AND-CHANGE-MANAGEMENT.md).

## Observed practice and recommended lifecycle

Observed repository practice uses focused changes, tests, documentation updates, and explicit checkpoint evidence. The recommended lifecycle is: need or issue -> classify -> inspect authoritative documents -> implement -> validate -> update documentation -> review -> release gate -> non-force integration -> checkpoint handoff.

## Change classes

| Change | Minimum documentation and validation impact |
| --- | --- |
| Product behavior | Product/technical specifications; affected feature tests. |
| Backend/API or database | API/database/data-model documents; focused contract, job, or migration tests. |
| Frontend/UX | UX/design/content/accessibility documents as applicable; build and frontend tests. |
| Security or deployment | Security/operations or deployment/release documents; applicable security/build checks. |
| Measurement/scoring | Product specification and ADR if architectural; semantics/scoring/measurement tests. |
| Documentation | Link, anchor, metadata, path, and diff checks. |

## Definition of ready — recommended

State the intended behavior, affected trust boundary, evidence source, dependencies, and documentation impact. Identify unresolved product/UX or infrastructure decisions before implementation. This is not a formally approved intake process.

## Definition of done — recommended

The change has focused implementation and tests, applicable quality gates, updated authoritative documentation, and review appropriate to its risk. External checks, product approval, or deployment confirmation remain explicitly not verified until evidence exists.

## Review and handoff

Use code/document review as appropriate; request security/release confirmation for trust-boundary changes, product/UX confirmation for user-facing interpretation, and an ADR for significant architecture. Use [CHECKPOINT](CHECKPOINT.md) as the current-state handoff rather than recreating it in issue text.
