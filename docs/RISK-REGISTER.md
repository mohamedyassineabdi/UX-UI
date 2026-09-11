# Risk Register

**Status:** Current evidence-based risk register
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Maintainers, operators, product/UX stakeholders, and release reviewers
**Scope:** Known project risks and mitigations; distinct from blockers and decisions.
**Related documents:** [Security Operations](SECURITY_OPERATIONS.md), [Quality Gates](QUALITY-GATES.md), [Roadmap](ROADMAP.md), [Checkpoint](CHECKPOINT.md).

| ID | Risk | Category | Likelihood | Impact | Current mitigation | Residual risk | Status | Owner role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | SQLite/local artifacts cannot safely support multi-instance operation. | Architecture | Medium | High | Distributed mode fails; local transactions/leases serialize one host. | High until shared infrastructure is implemented. | Current | Engineering maintainer; infrastructure confirmation required |
| R-002 | Ephemeral deployments can lose criteria or retained artifacts. | Operations | Medium | High | Document external durable storage requirement. | Medium until storage is supplied and verified. | Current | Operator |
| R-003 | External auth, Figma, Appium, model, browser, and publication providers may be unavailable or misconfigured. | Dependency | Medium | Medium | Validate configuration and record unavailable checks. | Medium. | Current | Operator / engineering maintainer |
| R-004 | Automated evidence may be overinterpreted as full coverage, accessibility conformance, or field performance. | Product quality | Medium | High | Bounded coverage, provenance, laboratory-data, and review language. | Medium; human review remains required. | Current | Product/UX stakeholder |
| R-005 | Five-axis scores are used without approved calibration or KPI interpretation. | Product decision | Medium | High | Mark calibration/KPI approval proposed. | High until confirmation. | Current | Product/UX stakeholder |
| R-006 | Local Windows OpenSSL abort prevents auth integration verification on this machine. | Validation environment | Medium | Medium | Run deterministic remainder and security suite; retry on target environment. | Medium. | Current | Engineering maintainer |
| R-007 | Docker image validation cannot run locally while the daemon is unavailable. | Validation environment | Medium | Medium | CI/Docker-capable environment must verify build. | Medium. | Current | Operator / release reviewer |
| R-008 | Raw JSON review input and missing visible interrupted state create UX/accessibility friction. | Product UX | High | Medium | Gaps are documented; server lifecycle remains authoritative. | Medium. | Current | Product/UX stakeholder; frontend engineer |

## Blockers kept separate

- **Release prerequisite:** confirmation of inherited credential remediation is not established; see [Security Operations](SECURITY_OPERATIONS.md).
- **External verification:** local Docker and auth-integration limitations are not failures of the deterministic remainder, but are not verified checks.

## Open decisions kept separate

Score calibration/KPI approval, hosted screenshot/mobile scope, and distributed deployment need confirmation; see the [Roadmap](ROADMAP.md). No risk entry makes those decisions approved.
