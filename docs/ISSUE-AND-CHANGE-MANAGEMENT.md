# Issue and Change Management

**Status:** Recommended evidence-based change handling
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Contributors, maintainers, reviewers, and product/UX stakeholders
**Scope:** Triage, escalation, and traceability; no SLA or workflow tool is established.
**Related documents:** [Delivery Process](DELIVERY-PROCESS.md), [Decisions](DECISIONS.md), [Risk Register](RISK-REGISTER.md), [Roadmap](ROADMAP.md).

## Change types and triage

Classify a report as a bug, product change, UX improvement, security issue, architecture change, data/schema change, deployment change, or documentation change. Triage should consider severity, user/security impact, evidence quality, reproducibility, trust-boundary impact, and deployment impact. No response SLA, ticket system, or named escalation path is established.

## Escalation and ADR threshold

Escalate credential/security concerns to the security/release confirmation boundary; architecture or schema changes to the engineering maintainer and [ADRs](DECISIONS.md); score interpretation and accessibility/compliance claims to product/UX confirmation; production release questions to the release/deployment boundary. Create or update an ADR for significant architectural decisions, not routine implementation details.

## Documentation impact

| Change | Documentation to assess |
| --- | --- |
| API behavior | [API Specification](API-SPECIFICATION.md), Product Specification if observable |
| Schema or persistence | [Database Specification](DATABASE-SPECIFICATION.md), [Data Model](DATA-MODEL.md) |
| UX or content | [UX Specification](UX-SPECIFICATION.md), Design System/Content/Accessibility as applicable |
| Configuration or deployment | [Configuration](CONFIGURATION.md), [Deployment](DEPLOYMENT.md), [Release Process](RELEASE-PROCESS.md) |
| Security | [Security](SECURITY.md), [Security Operations](SECURITY_OPERATIONS.md) |
| Measurement/scoring | Product Specification, [Decisions](DECISIONS.md), and relevant tests |
| Product requirement | [Product Requirements](PRODUCT-REQUIREMENTS.md), Product Specification, Roadmap if decision state changes |

## Traceability and unresolved work

Record the change's commit, focused tests, and documentation updates without treating a commit as approval. Keep risks in [RISK-REGISTER](RISK-REGISTER.md), current handoff facts in [CHECKPOINT](CHECKPOINT.md), and unresolved decisions in [ROADMAP](ROADMAP.md); do not duplicate their lists in each issue.
