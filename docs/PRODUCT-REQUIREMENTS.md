# Product Requirements

**Status:** Reconstructed product requirements; approval status is not established
**Repository baseline:** `main @ 5d9646c4daa221f43c82cd8d477144900193bdb0`
**Last updated:** 2026-09-10
**Audience:** Product, UX/UI, engineering, and delivery stakeholders
**Scope:** Why UX/UI Auditor exists and what it must provide; implementation details belong in the [Technical Specification](TECHNICAL-SPECIFICATION.md).
**Related documents:** [Product Specification](PRODUCT-SPECIFICATION.md), [Roadmap](ROADMAP.md), [Terminology](PRODUCT-SPECIFICATION.md#core-terminology).

## Purpose, vision, and problem

UX/UI Auditor makes it practical to turn an inspectable website, screenshot set, Android app, or Figma file into a reviewable UX/UI audit. It reduces the manual work of collecting evidence, documenting observed friction, and producing a consistent report before a specialist prioritizes improvements. It is a decision-support tool, not a certification authority.

## Users and stakeholders

| Group | Need |
| --- | --- |
| Primary users: UX/UI specialists | Collect comparable evidence, examine uncertainty, and refine a report. |
| Report consumers: product owners and delivery teams | See material risks, affected surfaces, severity, evidence, and suggested actions. |
| Operational actors: engineers/maintainers | Safely run, inspect, cancel, recover, and retain audit jobs. |

## Goals and in-scope capabilities

- `PRD-FR-001` Accept authenticated jobs for public website URLs, image uploads, Android sessions, and Figma URLs.
- `PRD-FR-002` Collect mode-appropriate evidence and issue a locally reviewable static report.
- `PRD-FR-003` For websites, record representative-sample collection coverage separately from check results.
- `PRD-FR-004` Present findings with severity and evidence; do not manufacture unsupported page attribution.
- `PRD-FR-005` Support the current five-axis audit taxonomy: **Performance & Task Execution** (runtime/task friction), **Flow & Architecture** (navigation and information path), **Trust & Accessibility** (visible trust and accessible interaction signals), **Visual & UI Consistency** (repeated pattern coherence), and **Content & Microcopy** (clarity of visible language/actions).
- `PRD-FR-006` Provide durable job status, progress, cancellation, protected report access, and user ownership boundaries.

## Non-goals

The baseline does not provide WCAG certification, legal compliance advice, penetration testing, field Core Web Vitals, exhaustive crawling, autonomous form/account/purchase activity, or safe multi-instance job coordination.

## Product-quality requirements

- `PRD-NFR-001` Conclusions must preserve uncertainty and distinguish observed evidence from model-assisted interpretation.
- `PRD-NFR-002` Website collection must reject unsafe public-URL inputs and avoid state-changing interactions.
- `PRD-NFR-003` Reports/artifacts must be protected by authenticated ownership and require durable storage if retained across ephemeral deployments.

## Success measures, dependencies, and assumptions

**Proposed - requires product approval:** audit completion rate, selected-page coverage ratio, reviewer acceptance/rejection of suggested findings, and time to a reviewable report. No approved KPI targets are in the repository.

Dependencies include portal authentication, Playwright, Figma authorization/API availability, an Appium-compatible Android runtime for live mobile audits, optional AI providers, and durable storage where deployment requires it. The Render configuration currently disables screenshot and live mobile jobs; that configuration does not establish the long-term product commitment.

## Risks and open product decisions

- **Needs confirmation:** score calibration and how stakeholders should interpret 0-100 scores.
- **Needs confirmation:** whether hosted screenshot/mobile operation is approved scope.
- Model output, Figma rate limits, and unavailable device runtimes can reduce or prevent an audit.
- Distributed deployment is **conditional**, pending a shared job store and artifact storage.
