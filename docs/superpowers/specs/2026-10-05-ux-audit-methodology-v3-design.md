# UX/UI Audit Methodology v3 — Design

- **Date:** 2026-10-05
- **Status:** Approved 2026-10-05
- **Supersedes:** methodology v2 (`shared/config/audit_axes.json` v2, `figma_audit/resources/ux_ui_criteria_validated.json`)

## 1. Goal

Make every audit report a correct, expert-grade UX/UI assessment:

- every finding is traceable to a named standard and to concrete evidence;
- the audit never claims more than it observed;
- the same methodology drives deterministic checks, AI review, scoring, and report text;
- audits are fast and token-efficient enough to run routinely.

## 2. Scope and decomposition

This work is split into sub-projects, each with its own spec → plan → implementation cycle:

| # | Sub-project | This spec |
|---|---|---|
| 1 | Methodology: taxonomy, criteria, severity, scoring | **Yes** (§3–§6) |
| 2 | AI pipeline and LLM prompt pack | **Yes** (§7–§8), design-level |
| 3 | Report content and structure (layered exec + practitioner) | Requirements only (§9) |
| 4 | Code migration of axis IDs (~30 files, 6 test files) | Requirements only (§10) |
| 5 | Locked recommendations + expert booking CTA | Separate spec |

Recommended build order: 1 → 2 → 4 → 3 → 5.

### Inputs and targets

- **Targets:** public websites, authenticated web apps, Figma designs, mobile (responsive viewports and native screens).
- **Audience:** layered — executive summary for client stakeholders, evidence-backed detail for designers and developers.
- **Report language:** selectable per audit (EN / FR).
- **Optional business context:** product type (e-commerce, SaaS, content, lead-gen, finance, public service), target users, key tasks (e.g. "checkout", "sign up").

## 3. Taxonomy — 7 axes

| # | id | Axis | Owns | Routes elsewhere |
|---|---|---|---|---|
| 1 | `usability` | Usability & Task Flow | Task completion, forms, system feedback, error prevention and recovery, user control (Nielsen H1, H3, H5, H7, H9) | Wording quality → 4; a11y barriers → 5 |
| 2 | `navigation` | Information Architecture & Navigation | Findability, wayfinding, labelling, search, menu structure (H4, H6) | In-task controls → 1 |
| 3 | `visual` | Visual Design & Hierarchy | Gestalt grouping, type scale, spacing, colour use, consistency / design-system adherence, interaction polish and motion | Contrast failures → 5 |
| 4 | `content` | Content & Microcopy | Plain language, CTA wording, scannability, help and instructional text (H2, H10) | Trust claims → 7 |
| 5 | `accessibility` | Accessibility & Inclusion | WCAG 2.2 AA (POUR), keyboard, screen reader, contrast, target size | General usability → 1 |
| 6 | `performance` | Performance & Responsiveness | LCP / INP / CLS, responsive layout, touch targets, mobile adaptation | Visual taste → 3 |
| 7 | `trust` | Trust & Credibility | Transparency (pricing, company, contact), security signals, consent and privacy, dark patterns, social proof | General copy → 4 |

Ownership rule: each logical problem is filed under exactly one axis — the axis that best explains the user impact. The `out_of_scope` list of every axis enforces this.

## 4. Axis and criterion schema

The config replaces `audit_axes.json` v2 and the criteria catalog with one source of truth (`shared/config/audit_methodology_v3.json`).

**Axis fields:** `id`, `name` {en, fr}, `core_question` {en, fr}, `why_it_matters` {en, fr}, `failure_modes[]`, `out_of_scope[]` (each with the target axis id), `criteria[]`.

**Criterion fields** (about 8–12 per axis, about 70 in total):

| Field | Purpose |
|---|---|
| `id` | Stable id, e.g. `usability.form_error_recovery` |
| `title`, `description` | {en, fr} |
| `weight` | `core` (3) or `supporting` (1) |
| `standards[]` | e.g. `WCAG22:1.4.3`, `NNG:H1`, `CWV:INP`, `GESTALT:proximity`, `BAYMARD:<topic>` |
| `targets[]` | Subset of `website`, `webapp`, `figma`, `mobile` |
| `page_types[]` | e.g. `form`, `checkout`, `listing`, `article`, `dashboard`, `any` |
| `evidence_type` | `measured` / `ai_assessed` / `manual_only` |
| `pass_guidance`, `fail_guidance` | Concrete bar shared by checks and AI |
| `example_good`, `example_rejected` | One well-formed finding; one generic finding that must not be produced |
| `logical_defect_family` | Dedupe key shared by all detectors of the same defect |

## 5. Severity

Four levels, based on the NN/g severity rating (impact × frequency × persistence):

| Level | Meaning | Example |
|---|---|---|
| Critical | Blocks a key task or excludes a user group; no workaround | Submit unreachable by keyboard; checkout error wipes form |
| High | Seriously hampers a key task; workaround exists | Failed login shows no message; LCP > 4 s |
| Medium | Friction or confusion; task still completes | Ambiguous CTA label; inconsistent button styles |
| Low | Cosmetic / polish | Uneven footer spacing |

**Context escalation:** a finding on a declared key-task path moves up one level (ceiling: Critical). The report states when escalation was applied.

## 6. Scoring

### 6.1 Evidence eligibility

| Evidence type | Counts toward score |
|---|---|
| `measured` | Always |
| `ai_assessed` | Only if confidence ≥ 0.8 **and** the finding cites element ids or a screenshot region; otherwise shown as an *Observation* with no score effect |
| `manual_only` | Only after an auditor confirms it in the review UI |

### 6.2 Axis score (0–100)

- Base = weighted pass rate over criteria that are applicable to the target and page types **and** were evaluated (core = 3, supporting = 1).
- Severity penalties are applied per failing logical defect (Critical > High > Medium > Low; exact values set during calibration).
- Deduplication is by `logical_defect_family` + target element + page. The same defect detected by axe, a custom check, and AI is penalised once. This resolves the DEDUPE_ERROR in `docs/METHODOLOGY_V2_VALIDATION.md`.

### 6.3 Coverage — always produce a score

An axis is never reported as "insufficient evidence". It is scored on whatever applicable criteria were evaluated, and the report shows a coverage line, e.g. *"Scored on 6 of 11 criteria — 5 not applicable to Figma (runtime behaviour)."* Criteria that do not apply to the target are excluded from the denominator, not counted as failures. An axis with zero applicable criteria for a target is omitted, and the report says why.

### 6.4 Maturity level (headline)

| Level | Label | Score band | Cap rule |
|---|---|---|---|
| 5 | Excellent | 90–100 | Requires no High or Critical |
| 4 | Good | 75–89 | Requires no Critical |
| 3 | Fair | 55–74 | — |
| 2 | Weak | 35–54 | Any Critical caps the axis here |
| 1 | Critical | 0–34 | — |

### 6.5 Overall

- Weighted average of scored axes. Weights are equal by default and adjusted by declared product type (e.g. `trust` weighted higher for e-commerce and finance, `usability` for SaaS). The weight table lives in config.
- Overall maturity uses the same bands, capped at (worst axis level + 1).

## 7. AI pipeline — fast and token-efficient

**Current problem:** the adjudicator calls the model once per page × criterion, resending up to 12k characters of page summary each time (`src/audit/checks/ai_review_layer.py`). The enricher then makes another call per check. Cost and latency scale as pages × criteria × 2.

**Design:**

1. **Deterministic first.** Measured results go straight to scoring. The AI only receives `ai_assessed` criteria, plus measured results that conflict or sit near a threshold.
2. **Page digest, built once per page** (~2–3k tokens): page type, heading outline, landmarks and nav, CTAs, form fields, and an inventory of interactive elements with stable ids `e1…eN` and bounding boxes. Cached by content hash + prompt version.
3. **Batch per axis.** One call evaluates all AI-assessed criteria of one axis for one page: ~3–4 calls per page.
4. **Screenshots:**
   - viewport only (above the fold + at most one key state), JPEG q≈70, 1280 px desktop / 390 px mobile;
   - Set-of-Mark overlay: numbered tags on interactive elements that match the digest ids;
   - the model cites ids; the tool draws issue boxes from the stored bounding boxes, so annotation is precise, model-independent, and costs no extra tokens;
   - images are sent only to the `visual`, `trust`, and `usability` calls.
5. **Template clustering.** Pages are grouped by DOM-structure signature / URL pattern. One representative per template gets the AI review; the others get deterministic checks only. Repeated findings are tagged *site-wide*.
6. **Cache-friendly prompt order:** role → rules → axis rubric → audit context → page evidence, so provider prompt caching reuses the fixed prefix.
7. **Compact outputs.** Per-page calls return strict JSON with failing findings in full, passes as an id list, and an output-token cap. Report prose (executive summary, priorities, roadmap) comes from **one synthesis call** over the merged findings.
8. **Parallel and progressive.** Bounded concurrency (4–8 calls). Deterministic results render immediately; AI findings stream in as they finish.
9. **Model tiering.** A fast model for per-page calls; a stronger model only for the final synthesis. Configured through the existing multi-provider `AIReviewClient`.

**Acceptance targets** (to be baselined against the current pipeline during planning):

- AI calls per audit ≤ (templates × 4) + 1;
- input tokens per page call ≤ 6k excluding images;
- report available with deterministic results immediately and complete within a target time agreed at planning.

## 8. LLM prompt pack

Prompts are generated from the methodology config, so they cannot drift from scoring rules.

| Layer | Content | Varies |
|---|---|---|
| 1. Role and principles | Senior UX/UI auditor; evidence rules; severity definitions; "not visible" ≠ "fail"; dedupe rules | Never (cached) |
| 2. Axis rubric | Criteria ids, standards, pass/fail guidance, good and rejected example | Per axis (cached) |
| 3. Audit context | Target, product type, users, key tasks, language | Per audit |
| 4. Page evidence | Digest, marked screenshots, deterministic results to confirm or contest | Per page |
| 5. Output contract | JSON schema | Never |

**Mandatory rules for any model:**

1. Every finding cites a `criterion_id` and `element_ids` (or a screenshot region).
2. Never judge what is not in the evidence: hover states, other pages, behaviour not shown.
3. Finding shape: observation → user impact → specific fix → severity with rationale → confidence.
4. No generic advice; prefer fewer, sharper findings.
5. Do not re-report deterministic findings; only confirm or contest them.
6. Write user-facing text in the audit language.

**Portability:** a plain JSON schema with no provider-specific features, validated with the existing pydantic schemas plus one retry.

**Standalone brief:** `AUDIT-AGENT-BRIEF.md` is generated from the same config so a human can run the methodology in any chat LLM with screenshots.

**Quality gate:** a golden set of 5 reference sites with expert-annotated findings in `evaluation/`. Each prompt version is scored for precision and recall before release.

## 9. Report requirements (input to sub-project #3)

- **Executive layer:** overall maturity and score; per-axis maturity with coverage line; top 5 issues by severity × key-task relevance; business-impact framing.
- **Practitioner layer:** findings grouped by axis, each with annotated screenshot, standard reference, observation, impact, fix, severity, confidence, evidence type, and a site-wide or page-specific tag.
- Observations (below the AI confidence gate) are listed separately and clearly labelled as unscored.
- All user-facing strings come from the config / synthesis in the selected language.

## 10. Migration requirements (input to sub-project #4)

- Map v2 axis ids to v3: `task_execution` → `usability` (+ runtime metrics → `performance`), `flow_architecture` → `navigation`, `trust_accessibility` → `accessibility` (+ trust signals → `trust`), `ui_consistency` → `visual`, `content_microcopy` → `content`.
- Existing reports stay readable: stored results keep their methodology version, and the UI renders by version.
- Update the ~30 referencing files and 6 test files (`tests/test_axis_definitions_v2.py`, `test_methodology_v2_scoring.py`, `test_phase3a_scoring.py`, `test_phase3b_measurement.py`, `test_gtm_axe_scoring.py`, `test_frontend_browser.py`).

## 11. Testing

- Config schema validation: every criterion has standards, targets, evidence type, and guidance in both languages.
- Scoring unit tests: weighted pass rate, severity penalties, cap rules, coverage exclusion, dedupe by logical family, context escalation, product-type weights.
- Controlled scenarios carried over from the v2 validation study (A–J), re-expressed on v3 axes.
- AI pipeline: call-count and token-budget assertions on a fixture audit; schema-retry behaviour; a template-clustering fixture.
- Golden-set evaluation for prompt quality (§8).

## 12. Out of scope

- Locked recommendations and expert booking (sub-project #5, separate spec).
- Real-user analytics or user-testing data.
- Changing the crawler or authentication mechanisms.
