# Release Plan

**Status:** Current release-scope and readiness view; not a release commitment
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-15
**Audience:** Maintainers, operators, product/UX stakeholders, and release reviewers
**Scope:** Planned-release scope, prerequisites, and decisions; execution is in [Release Process](RELEASE-PROCESS.md).
**Related documents:** [Release Process](RELEASE-PROCESS.md), [Quality Gates](QUALITY-GATES.md), [Deployment](DEPLOYMENT.md), [Roadmap](ROADMAP.md), [Checkpoint](CHECKPOINT.md).

## Current release scope

Implemented product capability includes website, screenshot, Figma, and Android/mobile audit inputs; evidence/provenance, measurement coverage, five-axis scoring, structured review, and immutable publication snapshots. Capability is distinct from hosted runtime availability.

## Readiness and prerequisites

| Category | Current status | Evidence or next action |
| --- | --- | --- |
| Implemented behavior | Implemented | See Product and Technical Specifications. |
| Repository validation | Conditionally verified | Apply [Quality Gates](QUALITY-GATES.md) to the release scope. |
| External credential remediation | External confirmation required | Repository owner must confirm provider-side revocation/rotation; scanning cannot prove it. |
| Docker/local runtime | Not verified locally | Use a Docker-capable environment or CI evidence. |
| External modes/providers | Conditional | Verify auth, browser, Figma, Appium/device, models, Vercel, and storage where used. |

## Included and excluded scope

Distributed deployment, hosted screenshot/mobile enablement, and score calibration/KPI approval are not established release scope. Ephemeral deployments require external durable storage for retained artifacts and custom criteria. See [Roadmap](ROADMAP.md) for decision candidates.

## Release sequence

Prepare -> validate -> review -> integrate -> deploy where applicable -> verify. The detailed gate and rollback process is [Release Process](RELEASE-PROCESS.md); this plan does not replace it.

## Open decisions

Score calibration/KPI approval, hosted-mode scope, and any distributed-deployment requirement remain unresolved. No release date is established by the repository documentation.
