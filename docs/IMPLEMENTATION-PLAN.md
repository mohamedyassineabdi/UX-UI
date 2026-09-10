# Implementation Plan

**Status:** Evidence-based plan; not a management commitment
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-10
**Audience:** Engineering, product, and delivery stakeholders
**Scope:** Baseline delivery, in-progress work, and conditional/proposed phases.
**Related documents:** [Roadmap](ROADMAP.md), [Decisions](DECISIONS.md), [Checkpoint](CHECKPOINT.md).

## Completed baseline

### Baseline foundations

**Status:** Implemented / Accepted
**Objective:** Establish the single-instance audit baseline.
**Scope:** Isolated workspaces, durable local queued jobs, representative discovery/coverage, security controls, and four pipeline entry points.
**Dependencies:** Local filesystem, SQLite, and external mode runtimes.
**Tasks:** Completed in baseline commits.
**Out of scope:** Distributed deployment.
**Verification:** `c9eeda9`, `506ebed`, `5d9646c`, `e009a7f`, and current tests.
**Exit gate:** Satisfied for the single-instance baseline.

## Current baseline

Evidence/provenance semantics, measurement methodology, evidence-aware scoring, structured review, publication snapshots, and bundled frontend delivery are implemented in the remote baseline. The remaining work is validation/calibration and conditional deployment capability, not landing those features.

## Conditional work

### Distributed deployment

**Status:** Conditional - confirmation required
**Objective:** Enable multiple instances safely.
**Scope:** Shared job backend and durable artifact storage.
**Dependencies:** An approved operational requirement and infrastructure.
**Tasks:** Implement locking/migration, topology, backup/recovery, and concurrency testing.
**Out of scope:** Treating SQLite as distributed coordination.
**Verification required:** Demonstrate concurrent claim and recovery behavior.
**Exit gate:** Multi-instance runbook and verification evidence.

### Hosted screenshot and mobile operation

**Status:** Conditional - confirmation required
**Objective:** Enable modes disabled by current Render configuration.
**Scope:** Hosted screenshot and live-mobile operation.
**Dependencies:** Compatible model/Appium runtime and capacity controls.
**Tasks:** Run secured end-to-end tests and explicitly enable the environment.
**Out of scope:** Expanding audit modalities.
**Verification required:** Run a successful secured hosted test.
**Exit gate:** Explicit environment enablement with test evidence.

## Proposed work

### Score calibration and reviewer validation

**Status:** Proposed
**Objective:** Establish reviewer-agreed interpretation of five-axis scores.
**Scope:** Calibration and reviewer validation.
**Dependencies:** Product/UX participation and curated fixtures.
**Tasks:** Agreement analysis, threshold/score-cap review, and proposed success measures.
**Out of scope:** Claiming approved business KPIs.
**Verification required:** Complete reviewer agreement analysis.
**Exit gate:** Recorded product/UX approval.
