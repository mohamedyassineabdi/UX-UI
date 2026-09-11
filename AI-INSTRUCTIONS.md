# AI Instructions

**Status:** Operating guidance for AI-assisted repository work
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** AI/code agents and maintainers
**Scope:** Safe, evidence-based operating rules; supplements human review and authoritative project documents.
**Related documents:** [Project Context](PROJECT-CONTEXT.md), [Reading Map](READING-MAP.md), [Execution Rules](EXECUTION-RULES.md), [Security](docs/SECURITY.md).

## Inspect before changing

Fetch, inspect branch/status, read the task-relevant documents, source, configuration, tests, and recent history before acting. Do not infer current behavior from an old document, a commit title, or a recommendation.

## Source-of-truth hierarchy

1. Current committed code, tests, and runtime/configuration establish implemented behavior.
2. Technical, Architecture, API, Database, and Security documents define recorded contracts and boundaries.
3. Product Requirements and Product Specification define product-facing terminology and behavior.
4. ADRs record engineering decisions; planning/checkpoint documents record status and candidates.
5. UX, design, content, accessibility, analytics, and project-process documents must retain their stated implemented/recommended/proposed boundary.

If sources conflict, investigate and identify the stale source. Change code or documentation only within the requested scope; never silently choose one.

## Implementation is not a recommendation

Use the document’s exact status: **Implemented/current**, **observed convention**, **recommended**, **proposed**, **conditional**, **not implemented**, or **needs confirmation**. In particular, do not claim WCAG compliance, dedicated product analytics, approved score calibration/KPIs, hosted screenshot/mobile availability, distributed deployment, or a formally adopted management process without current evidence. AI/model output is evidence-bound probabilistic enrichment, not verified fact.

## No-hallucination and documentation sync

Never invent routes, tables, variables, tests, flags, tokens, telemetry, KPIs, owners, dates, SLAs, infrastructure, approvals, or compliance claims. Update authoritative documents with behavior changes: API -> API Specification (and Product Specification if observable); schema -> Database Specification/Data Model; security -> Security/Security Operations; UX -> UX/Design/Content/Accessibility; configuration -> Configuration; deployment -> Deployment/Release Process; architecture -> Architecture/Decisions.

## Validation and security

Follow [Testing](docs/TESTING.md) and [Quality Gates](docs/QUALITY-GATES.md). Report only **PASSED**, **FAILED**, **NOT VERIFIED**, **EXTERNAL INTEGRATION NOT VERIFIED**, or **SKIPPED** as evidence supports; an aborted test is not passed. Never expose credentials, weaken authentication/network controls casually, bypass secret scanning, or treat repository scanning as proof of external credential remediation.

## Git and scope safety

Inspect status before Git operations. Protect dirty user work: do not reset, clean, stash, rebase, or overwrite it without explicit authorization and a justified target. Prefer a clean worktree; fetch before integration; stage explicit paths instead of `git add .` in mixed scope; do not force-push or bypass branch protection. A documentation task does not authorize application changes or unrelated fixes.

## Reporting

Separate observed facts from inference, name blockers and unverified checks, and report exact branch/commit/result details where useful.
