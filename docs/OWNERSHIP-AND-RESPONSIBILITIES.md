# Ownership and Responsibilities

**Status:** Recommended role-based responsibility boundary
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Maintainers, reviewers, operators, and product/UX stakeholders
**Scope:** Responsibility boundaries without named assignments or a formal adopted RACI.
**Related documents:** [Project Plan](PROJECT-PLAN.md), [Release Process](RELEASE-PROCESS.md), [Security Operations](SECURITY_OPERATIONS.md), [Checkpoint](CHECKPOINT.md).

No named owner, staffing assignment, or formal RACI is established by repository evidence. The following is a recommended responsibility boundary, not an assignment record.

| Area | Responsible role | Confirmation required from | Consulted / operational role |
| --- | --- | --- | --- |
| Product requirements and score interpretation | Product/UX stakeholder | Product/UX stakeholder | Engineering maintainer |
| UX, content, and accessibility claims | UX/UI specialist | Product/UX stakeholder | Frontend engineer, accessibility reviewer |
| Architecture, API, schema, and implementation | Engineering maintainer | Architecture decision record where significant | Reviewer |
| Security controls and credential remediation | Engineering maintainer | Security/release owner | Operator |
| Deployment, durable storage, and external configuration | Operator | Release owner | Engineering maintainer |
| Criteria configuration and audit operation | Admin / operator | Product/UX stakeholder where interpretation changes | Reviewer |
| Audit review, approval, and publication | Owner-scoped reviewer | Product/UX or release confirmation when required | Operator |
| Incident response | Operator / security-release owner | Repository owner where external action is required | Engineering maintainer |
| Documentation and checkpoint handoff | Change author / engineering maintainer | Relevant reviewer | Product/UX stakeholder as needed |

The application enforces authenticated owner access for audit/report/review/publication records; that technical ownership does not identify a real-world person or establish release authority.
