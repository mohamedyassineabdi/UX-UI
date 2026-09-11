# Milestones

**Status:** Factual milestone register
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Maintainers, product/UX stakeholders, and delivery reviewers
**Scope:** Technical and documentation checkpoints; no schedule or approval record.
**Related documents:** [Project Plan](PROJECT-PLAN.md), [Implementation Plan](IMPLEMENTATION-PLAN.md), [Checkpoint](CHECKPOINT.md).

| Milestone | Status | Evidence | Exit condition | Notes |
| --- | --- | --- | --- | --- |
| Isolated audit workspaces | Completed | `c9eeda9`; `tests/test_audit_workspace.py` | Implemented isolation tests pass | Technical milestone, not distributed storage. |
| Queued SQLite job lifecycle | Completed | `506ebed`; `tests/test_job_queue.py` | Job/lease lifecycle tests pass | Single-instance only. |
| Representative website sampling | Completed | `5d9646c`; `tests/test_discovery_scope.py` | Bounded scope/coverage tests pass | Not a full crawl. |
| Result provenance, measurement, scoring | Completed | `32aee32`, `1e4a55a`, `3f5ae54`; phase tests | Semantics/scoring/measurement tests pass | Calibration remains proposed. |
| Review and publication workflow | Completed | `67b5a77`; review/publication tests | Transition and snapshot tests pass | External publication remains conditional. |
| React/Vite frontend bundling | Completed | `b49d8ac`; frontend build/security tests | Production build succeeds | Python serves built assets. |
| Phase 1 core documentation | Completed | `bfb3c95` | Published on `origin/main` | Documentation milestone. |
| Phase 2 engineering documentation | Completed | `786eae6`, `69b7aca` | Published on `origin/main` | Documentation milestone. |
| Phase 3 product/UX documentation | Completed | `cc86999` | Published on `origin/main` | Documentation milestone. |
| Phase 4 delivery documentation | Completed | `1bb6b19` | Published and integrated on `origin/main` | No management approval implied. |
| Score calibration and reviewer validation | Proposed | [Implementation Plan](IMPLEMENTATION-PLAN.md#score-calibration-and-reviewer-validation) | Recorded product/UX approval | No KPI target established. |
| Hosted screenshot/mobile operation | Conditional | [Roadmap](ROADMAP.md) | Compatible secured runtime and test evidence | Current Render configuration disables it. |
| Distributed deployment | Conditional | [Implementation Plan](IMPLEMENTATION-PLAN.md#distributed-deployment) | Approved requirement and shared-store/artifact evidence | SQLite is not distributed coordination. |
