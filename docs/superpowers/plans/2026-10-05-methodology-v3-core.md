# Methodology v3 Core (Taxonomy, Criteria, Severity, Scoring) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Per the user's preference, this plan is lean: it specifies files, interfaces, behaviours, and test cases, not full code.

**Goal:** Ship the v3 methodology as a validated config plus a pure-Python scoring library (7 axes, ~70 criteria, 4-level severity, score + maturity + coverage, product-type weights), side by side with v2 and not yet wired into the pipeline.

**Architecture:** One config file (`shared/config/audit_methodology_v3.json`) is the single source of truth, loaded into frozen pydantic models. A new package `src/gtm_audit/methodology_v3/` holds focused modules — config loading, severity, eligibility, axis scoring, overall scoring, and the v2-rule → v3-criterion map. v2 code in `src/gtm_audit/scoring.py` and `rule_registry.py` is untouched; wiring v3 into generation is sub-project #4.

**Tech Stack:** Python 3, pydantic v2 (already a dependency), pytest.

**Spec:** `docs/superpowers/specs/2026-10-05-ux-audit-methodology-v3-design.md` (§3–§6, §10–§11)

## Global Constraints

- Axis ids, in this order: `usability`, `navigation`, `visual`, `content`, `accessibility`, `performance`, `trust`.
- Every user-facing string is `{en, fr}`; both are non-empty.
- Criterion weight: `core` = 3, `supporting` = 1.
- Evidence types: `measured` (always eligible); `ai_assessed` (eligible only if confidence ≥ 0.8 **and** at least one `elementIds` entry or a `screenshotRegion`); `manual_only` (eligible only when `reviewStatus == "confirmed"`).
- Severity levels: `critical`, `high`, `medium`, `low`. Key-task escalation raises by one level, with `critical` as the ceiling.
- Initial penalties (in config, calibratable): critical 25, high 12, medium 5, low 1.
- Maturity bands: 5 Excellent 90–100 (requires no high or critical) · 4 Good 75–89 (requires no critical) · 3 Fair 55–74 · 2 Weak 35–54 · 1 Critical 0–34. Any critical caps the axis at 2.
- Never return "insufficient evidence": score on evaluated applicable criteria and attach coverage. Omit an axis only when zero criteria apply to the target.
- Overall maturity is capped at (worst axis level + 1).
- All existing v2 tests keep passing; no v2 module is modified.

## Review Focus

1. **Unknown `criterionId` on a row** (typo, or a new check not yet in config) → reported as unscored; no exception. Test added in Task 4.
2. **Rows with no target / page / element** → two distinct defects in the same family must stay two consequences. This is the v2 DEDUPE_ERROR. Test added in Task 4.
3. **Figma target where most criteria are runtime-only** → a score is still produced from the evaluated criteria, with a coverage line; never `None` unless zero criteria apply. Test added in Task 4.
4. **Confidence given as a numeric string (`"0.85"`) or a percentage (`85`)** → normalised to 0–1 (values > 1 are divided by 100; unparsable values become 0). Test added in Task 3.
5. **Unknown or missing `product_type`** → equal weights, no error. Test added in Task 5.

---

## File Structure

| File | Responsibility |
|---|---|
| `shared/config/audit_methodology_v3.json` | Axes, criteria, severity penalties, maturity bands, product-type weights |
| `src/gtm_audit/methodology_v3/__init__.py` | Public re-exports |
| `src/gtm_audit/methodology_v3/config.py` | pydantic models + `load_methodology()` (cached) |
| `src/gtm_audit/methodology_v3/severity.py` | Severity enum, escalation |
| `src/gtm_audit/methodology_v3/eligibility.py` | Confidence normalisation, score eligibility |
| `src/gtm_audit/methodology_v3/scoring.py` | Dedupe, `score_axis_v3`, maturity, `overall_v3` |
| `src/gtm_audit/methodology_v3/rule_map.py` | v2 emitted rule key → v3 criterion id |
| `scripts/render_methodology_doc.py` | Renders `docs/METHODOLOGY_V3.md` from config |
| `tests/test_methodology_v3_config.py`, `_scoring.py`, `_rule_map.py`, `_scenarios.py` | Tests |

---

### Task 1: Config models, loader, and validation rules

**Files:**
- Create: `src/gtm_audit/methodology_v3/__init__.py`, `config.py`
- Create: `shared/config/audit_methodology_v3.json` (skeleton: 7 axes with identity fields, `scoring` block, `productTypeWeights`; one placeholder-free sample criterion per axis so validation passes; full criteria come in Task 2)
- Test: `tests/test_methodology_v3_config.py`

**Interfaces — produces:**
- `LocalizedText(en: str, fr: str)`
- `Criterion(id, title: LocalizedText, description: LocalizedText, weight: Literal["core","supporting"], standards: tuple[str,...], targets: tuple[Literal["website","webapp","figma","mobile"],...], page_types: tuple[str,...], evidence_type: Literal["measured","ai_assessed","manual_only"], pass_guidance: LocalizedText, fail_guidance: LocalizedText, example_good: LocalizedText, example_rejected: LocalizedText, logical_defect_family: str)`, plus a property `numeric_weight -> int` (3 or 1)
- `OutOfScope(topic: str, routes_to: str)`
- `Axis(id, name, core_question, why_it_matters: LocalizedText, failure_modes: tuple[LocalizedText,...], out_of_scope: tuple[OutOfScope,...], criteria: tuple[Criterion,...])`
- `ScoringConfig(penalties: dict[str,int], ai_confidence_gate: float, maturity_bands: tuple[MaturityBand,...])`, where `MaturityBand(level: int, label: LocalizedText, min_score: int)`
- `Methodology(version: Literal[3], axes: tuple[Axis,...], scoring: ScoringConfig, product_type_weights: dict[str, dict[str,float]])`, with methods `axis(axis_id) -> Axis` and `criterion(criterion_id) -> Criterion | None`
- `load_methodology(path: Path | None = None) -> Methodology`; default path from env `AUDIT_METHODOLOGY_V3_PATH`, else the shared config; `functools.lru_cache` on the default path only

**Validation rules (pydantic `model_validator`s), each with a failing-config test:**
- Axis ids exactly match the Global Constraints order.
- Criterion ids are unique and prefixed `<axis_id>.`.
- `standards` is non-empty, and each entry matches `^(WCAG22:\d\.\d+\.\d+|NNG:H(10|[1-9])|CWV:(LCP|INP|CLS|FCP|TTFB)|GESTALT:\w+|BAYMARD:[\w-]+|ISO9241:[\w.-]+|NNG:[\w-]+|STANFORD:[\w-]+)$`.
- `targets` is non-empty.
- `out_of_scope.routes_to` is another valid axis id.
- `penalties` has exactly the 4 severity keys.
- Maturity bands are levels 5..1 with descending `min_score`.
- `productTypeWeights` keys are axis ids with positive values.
- `fr` is non-empty everywhere.

- [ ] Step 1: Write the tests: a valid fixture loads with 7 axes in order; each rule above has its own test that mutates a deep copy of the fixture and asserts `pydantic.ValidationError`; `methodology.criterion("nope")` is `None`.
- [ ] Step 2: Run `python -m pytest tests/test_methodology_v3_config.py -v`. Expect FAIL (module missing).
- [ ] Step 3: Implement the models, loader, and skeleton JSON.
- [ ] Step 4: Re-run. Expect PASS. Also run `python -m pytest tests/test_axis_definitions_v2.py -q` and expect PASS (v2 untouched).
- [ ] Step 5: Commit `feat(methodology-v3): add config models and validated loader`.

### Task 2: Author the full criteria set (expert content)

**Files:**
- Modify: `shared/config/audit_methodology_v3.json`
- Test: `tests/test_methodology_v3_config.py` (content-level tests)

Author every criterion with all fields in EN and FR. `pass_guidance` / `fail_guidance` must name a concrete, checkable bar (thresholds, counts, states), never "is good". `example_rejected` must be a generic finding that cites no element (it teaches the AI what not to produce). Criteria to author — `id` (weight · main standards · evidence type):

**usability**
- `primary_action_clear` (core · NNG:H6, BAYMARD:cta · ai_assessed)
- `action_feedback` (core · NNG:H1 · measured)
- `loading_state_feedback` (supporting · NNG:H1 · measured)
- `form_requirements_upfront` (core · WCAG22:3.3.2, NNG:H5 · measured)
- `form_input_effort` (supporting · BAYMARD:form-fields, WCAG22:1.3.5 · measured)
- `inline_validation` (supporting · NNG:H9 · measured)
- `error_recovery` (core · NNG:H9, WCAG22:3.3.3 · measured)
- `destructive_action_safeguard` (supporting · NNG:H5, WCAG22:3.3.4 · manual_only)
- `user_control_exit_undo` (supporting · NNG:H3 · ai_assessed)
- `task_completion_confirmation` (core · NNG:H1 · manual_only)

**navigation**
- `global_nav_present` (core · NNG:H6 · measured)
- `current_location_indicated` (core · NNG:H1, WCAG22:2.4.8 · measured)
- `nav_label_scent` (supporting · NNG:information-scent · ai_assessed)
- `nav_structure_depth` (supporting · NNG:H8 · measured)
- `consistent_navigation` (core · WCAG22:3.2.3, NNG:H4 · measured)
- `search_where_expected` (supporting · BAYMARD:search · measured)
- `breadcrumbs_deep_hierarchy` (supporting · NNG:breadcrumbs · measured)
- `no_dead_ends` (core · NNG:H3 · measured)
- `logo_links_home` (supporting · NNG:H4 · measured)

**visual**
- `visual_hierarchy` (core · GESTALT:figure_ground, NNG:H8 · ai_assessed)
- `gestalt_grouping` (core · GESTALT:proximity · ai_assessed)
- `typographic_scale` (supporting · ISO9241:125 · measured)
- `readable_line_length` (supporting · ISO9241:125 · measured; bar 45–75 characters)
- `spacing_rhythm` (supporting · GESTALT:similarity · measured)
- `colour_purpose` (supporting · GESTALT:similarity · ai_assessed)
- `component_consistency` (core · NNG:H4 · measured)
- `button_hierarchy` (supporting · NNG:H8 · measured)
- `affordance_clarity` (supporting · NNG:affordances · ai_assessed)
- `purposeful_motion` (supporting · NNG:animation-usability · measured; bar 150–400 ms UI transitions, honours reduced-motion)

**content**
- `value_proposition_clear` (core · NNG:H2 · ai_assessed)
- `plain_language` (core · NNG:H2, ISO9241:110 · measured)
- `descriptive_cta_labels` (core · NNG:H2 · measured)
- `scannable_structure` (supporting · NNG:scanning · measured)
- `consistent_terminology` (supporting · NNG:H4 · measured)
- `helpful_error_wording` (supporting · NNG:H9 · ai_assessed; owns wording, while `usability.error_recovery` owns the mechanism)
- `instructional_text` (supporting · NNG:H10 · ai_assessed)
- `reassurance_microcopy` (supporting · BAYMARD:checkout · ai_assessed)

**accessibility**
- `text_contrast` (core · WCAG22:1.4.3 · measured)
- `non_text_contrast` (supporting · WCAG22:1.4.11 · measured)
- `text_alternatives` (core · WCAG22:1.1.1 · measured)
- `keyboard_operable` (core · WCAG22:2.1.1, WCAG22:2.1.2 · measured)
- `focus_visible` (core · WCAG22:2.4.7, WCAG22:2.4.11 · measured)
- `focus_order` (supporting · WCAG22:2.4.3 · measured)
- `names_labels` (core · WCAG22:1.3.1, WCAG22:4.1.2, WCAG22:3.3.2 · measured)
- `structure_headings_landmarks` (supporting · WCAG22:1.3.1, WCAG22:2.4.6 · measured)
- `target_size` (supporting · WCAG22:2.5.8 · measured)
- `reflow_zoom` (supporting · WCAG22:1.4.10, WCAG22:1.4.4 · measured)
- `link_purpose` (supporting · WCAG22:2.4.4 · measured)
- `motion_control` (supporting · WCAG22:2.2.2, WCAG22:2.3.3 · measured)

**performance**
- `lcp` (core · CWV:LCP · measured; good ≤ 2.5 s, poor > 4 s)
- `inp` (core · CWV:INP · measured; good ≤ 200 ms, poor > 500 ms)
- `cls` (core · CWV:CLS · measured; good ≤ 0.1, poor > 0.25)
- `first_render` (supporting · CWV:FCP, CWV:TTFB · measured)
- `asset_weight` (supporting · CWV:LCP · measured)
- `responsive_no_horizontal_scroll` (core · WCAG22:1.4.10 · measured)
- `viewport_configured` (supporting · WCAG22:1.4.4 · measured)
- `mobile_content_parity` (supporting · NNG:mobile-ux · ai_assessed)
- `font_loading_stability` (supporting · CWV:CLS · measured)

**trust**
- `company_identity_contact` (core · STANFORD:verifiable-identity · measured)
- `pricing_transparency` (core · BAYMARD:pricing · ai_assessed)
- `security_signals` (supporting · STANFORD:security · measured)
- `consent_fair_choice` (core · NNG:deceptive-patterns · ai_assessed; reject is as easy as accept)
- `no_deceptive_patterns` (core · NNG:deceptive-patterns · ai_assessed; covers fake urgency, confirmshaming, pre-ticked boxes, hidden costs)
- `credible_social_proof` (supporting · STANFORD:third-party-support · ai_assessed)
- `policies_accessible` (supporting · STANFORD:transparency · measured)
- `content_freshness` (supporting · STANFORD:updated-content · measured)
- `professional_polish` (supporting · STANFORD:professional-design · measured; broken images, placeholder text)

**Targets rule:** runtime-only criteria (`action_feedback`, `loading_state_feedback`, `inline_validation`, `error_recovery`, `keyboard_operable`, `focus_order`, `lcp`, `inp`, `cls`, `first_render`, `asset_weight`, `font_loading_stability`, `motion_control`, `no_dead_ends`) exclude `figma`. All others include all four targets unless they are clearly web-only (e.g. `viewport_configured` excludes `figma`).

- [ ] Step 1: Add content tests:
  - each axis has 8–12 criteria;
  - each axis has ≥ 2 core criteria;
  - ids match the list above exactly (a frozen set in the test);
  - every `example_rejected` contains no `e\d+` element reference;
  - the runtime-only criteria above exclude `figma`;
  - no two criteria share a `logical_defect_family` across different axes.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Author the JSON.
- [ ] Step 4: Run `python -m pytest tests/test_methodology_v3_config.py -v`. Expect PASS.
- [ ] Step 5: Commit `feat(methodology-v3): author 7-axis criteria set with standards`.

### Task 3: Severity and score eligibility

**Files:**
- Create: `src/gtm_audit/methodology_v3/severity.py`, `eligibility.py`
- Test: `tests/test_methodology_v3_scoring.py`

**Interfaces — produces:**
- `Severity(str, Enum)`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, with `rank` (critical = 0)
- `escalate(severity: Severity, on_key_task: bool) -> tuple[Severity, bool]`; the bool is "escalated"
- `normalize_confidence(value: object) -> float`
- `is_score_eligible(row: dict, criterion: Criterion, gate: float) -> bool`. Row fields used: `confidence`, `elementIds`, `screenshotRegion`, `reviewStatus`.

- [ ] Step 1: Tests:
  - escalation table for all 4 levels, with and without a key task (critical stays critical and is reported `escalated=False`);
  - confidence normalisation of `"0.85"`, `85`, `None`, `"abc"`, `1.4` (→ 0.014; document that only values > 1 are percentages);
  - eligibility matrix: measured → True; ai_assessed at 0.8 with `elementIds` → True; at 0.79 → False; at 0.9 with no elements and no region → False; manual_only unconfirmed → False, confirmed → True.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(methodology-v3): severity escalation and evidence eligibility gate`.

### Task 4: Axis scoring, dedupe, maturity, coverage

**Files:**
- Create: `src/gtm_audit/methodology_v3/scoring.py`
- Test: `tests/test_methodology_v3_scoring.py`

**Interfaces:**
- Consumes: Task 1 models, Task 3 functions.
- Produces:
  - `FindingRow` contract (dict keys): `criterionId`, `outcome` (`pass|fail|warning|unknown`), `severity`, `onKeyTask`, `confidence`, `elementIds`, `screenshotRegion`, `pageId`, `reviewStatus`, `findingId`
  - `Coverage(evaluated: int, applicable: int, not_applicable_for_target: tuple[str,...], not_evaluated: tuple[str,...])`
  - `AxisScore(axis_id: str, score: float, maturity: int, maturity_label: LocalizedText, coverage: Coverage, worst_severity: Severity | None, scored_defects: int, observations: tuple[dict,...], escalations: tuple[str,...])`
  - `dedupe_key(row: dict, criterion: Criterion) -> str`
  - `score_axis_v3(rows: Iterable[dict], axis: Axis, target: str, scoring: ScoringConfig) -> AxisScore | None`
  - `maturity_for(score: float, worst: Severity | None, bands) -> int`

**Behaviour:**
- **Applicable criteria** are those with `target in criterion.targets`. If none apply, return `None`.
- **Rows:** a row whose `criterionId` is unknown or belongs to another axis is ignored (not counted, not raised).
- **Eligibility:** ineligible rows (Task 3) go into `observations` and do not affect the score.
- **Dedupe key** = `criterion.logical_defect_family | criterionId | pageId | sorted(elementIds)`. When `pageId` and `elementIds` are both absent, fall back to `findingId`, so distinct defects never collapse. Per key, keep the worst outcome, then the highest severity.
- **Criterion outcome:** `fail` if any kept row fails; `pass` if all kept rows pass; otherwise not evaluated. Warnings and unknowns count as not evaluated.
- **Base score** = 100 × Σ weight(passed criteria) / Σ weight(evaluated criteria). With 0 evaluated criteria, the score is 0.0, maturity 1, and coverage shows 0 of N. This is the "always produce a report" rule; the report layer shows the coverage line.
- **Penalty** = Σ penalties over distinct failing dedupe keys, after escalation. Score = clamp(base − penalty, 0, 100).
- **Maturity:** take the band from the score, then apply the caps (any critical → ≤ 2; any high → ≤ 4; level 5 requires no high or critical).

- [ ] Step 1: Tests:
  - all pass → 100 and level 5;
  - one core fail and one supporting pass → base 25, minus the medium penalty → 20, level 1;
  - a critical fail on an otherwise 95-scoring axis → maturity 2;
  - a high fail → maturity ≤ 4;
  - **Review Focus 1:** an unknown `criterionId` is ignored without error;
  - **Review Focus 2:** two rows, same family, different `findingId`, no page or elements → two penalties;
  - the same defect from axe + a custom check + AI (same page and elements) → one penalty;
  - **Review Focus 3:** target `figma` with 4 evaluated and 6 runtime-only criteria → score from the 4, with `coverage.not_applicable_for_target` listing the runtime ones;
  - zero applicable criteria → `None`;
  - key-task escalation applies and is recorded in `escalations`;
  - a low-confidence AI fail → appears in `observations` with the score unchanged.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(methodology-v3): axis scoring with dedupe, penalties, maturity caps, coverage`.

### Task 5: Overall score with product-type weights

**Files:**
- Modify: `src/gtm_audit/methodology_v3/scoring.py`
- Test: `tests/test_methodology_v3_scoring.py`

**Interfaces — produces:** `OverallScore(score: float, maturity: int, maturity_label: LocalizedText, weights_used: dict[str,float], axes_scored: int)` and `overall_v3(axis_scores: Iterable[AxisScore | None], product_type: str | None, methodology: Methodology) -> OverallScore`.

**Behaviour:**
- `None` axes are skipped, and weights are renormalised over the scored axes.
- An unknown or absent `product_type` → weight 1.0 for every axis.
- Overall maturity = the band from the weighted score, capped at min(axis maturity) + 1.

Seed `productTypeWeights` in config:
- `ecommerce`: trust 1.5, usability 1.3, performance 1.2
- `saas`: usability 1.5, navigation 1.2
- `content`: content 1.5, navigation 1.3
- `leadgen`: content 1.3, trust 1.3, usability 1.2
- `finance`: trust 1.6, accessibility 1.2
- `public_service`: accessibility 1.6, content 1.3
- every other axis: 1.0

- [ ] Step 1: Tests:
  - equal-weight average;
  - ecommerce weighting changes the result in the expected direction;
  - **Review Focus 5:** `product_type="spaceship"` and `None` → equal weights;
  - the cap (axes at levels 5, 5, 1 → overall ≤ 2);
  - all `None` → score 0, maturity 1, `axes_scored` 0.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(methodology-v3): weighted overall score with maturity cap`.

### Task 6: v2 rule → v3 criterion map

**Files:**
- Create: `src/gtm_audit/methodology_v3/rule_map.py`
- Test: `tests/test_methodology_v3_rule_map.py`

**Interfaces — produces:** `RULE_CRITERION_MAP_V3: dict[str, str]` (v2 emitted key such as `Content:16` or a machine criterion → v3 criterion id) and `criterion_for_rule(rule_key: str) -> str | None`.

**Mapping guidance** (follows spec §10):
- v2 `task_execution` → `usability.*`, except rules whose `dedupe_family` or subfacet is performance or runtime responsiveness → `performance.*`.
- `flow_architecture` → `navigation.*`.
- `trust_accessibility` → `accessibility.*`, except trust-signal rules → `trust.*`.
- `ui_consistency` → `visual.*`.
- `content_microcopy` → `content.*`.
- Pick the specific criterion by the v2 subfacet (e.g. subfacet `contrast` → `accessibility.text_contrast`).

- [ ] Step 1: Tests:
  - every key in `RULE_REGISTRY` with `score_eligible=True` maps to an existing v3 criterion;
  - the mapped criterion's axis is consistent with the v2 axis per the guidance (table-driven over a dict `V2_TO_V3_AXES = {"task_execution": {"usability","performance"}, "flow_architecture": {"navigation"}, "trust_accessibility": {"accessibility","trust"}, "ui_consistency": {"visual"}, "content_microcopy": {"content"}}`);
  - spot checks: `Content:16` → `accessibility.text_contrast`, `Navigation:9` → a `navigation.*` criterion;
  - unknown key → `None`.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement the map by walking `RULE_REGISTRY` subfacets.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(methodology-v3): map v2 rule keys to v3 criteria`.

### Task 7: Controlled scenarios, methodology doc, and full regression

**Files:**
- Create: `tests/test_methodology_v3_scenarios.py`, `scripts/render_methodology_doc.py`, `docs/METHODOLOGY_V3.md` (generated)
- Modify: `docs/DECISIONS.md` (add a v3 decision entry linking the spec)

- [ ] Step 1: Port scenarios A–J from `docs/METHODOLOGY_V2_VALIDATION.md` §5 to v3 axes as end-to-end tests over `score_axis_v3` + `overall_v3` (e.g. scenario H: LCP/FCP/TBT on one page → one `performance` consequence; scenario I: AI-only below the gate → observation only). Add a doc-freshness test: run `render_methodology_doc.render(load_methodology())` and assert it equals `docs/METHODOLOGY_V3.md`.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement the renderer: per axis, a table of criteria showing id, title (EN), weight, standards, targets, and evidence type, plus a severity table and maturity bands. Generate the doc.
- [ ] Step 4: Run `python -m pytest -q` (full suite). Expect all PASS, v2 included.
- [ ] Step 5: Commit `test(methodology-v3): controlled scenarios and generated methodology reference`.
