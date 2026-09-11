# Content Guidelines

**Status:** Current terminology plus explicitly labeled writing guidance
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Product, UX, content, and report authors
**Scope:** Product-facing terminology and evidence-aware communication; it does not alter stored technical state names.
**Related documents:** [Product Specification](PRODUCT-SPECIFICATION.md), [UX Specification](UX-SPECIFICATION.md), [Accessibility](ACCESSIBILITY.md).

## Current vocabulary

| Prefer | Meaning / avoid |
| --- | --- |
| Audit / audit mode | An assessment run; modes are website, screenshot, Figma, and Android/mobile. |
| Job | The queued/running execution record; avoid calling every artifact a job. |
| Finding / evidence / severity | Observation, its support, and practical impact. Do not imply evidence proves more than it does. |
| Collection coverage / measurement coverage | Selected-page completion / measured applicable-rule weight. Keep them distinct. |
| Score | Evidence-aware five-axis estimate, not certification or approved KPI. |
| Review / revision / validation / approval / publication | Separate lifecycle concepts; publication is not synonymous with validation. |
| Audit report | Preferred product-facing term; avoid legacy internal `GTM` outside implementation context. |

## Current status wording

Technical job states remain `queued`, `running`, `completed`, `failed`, `cancelled`, and `interrupted`. Current UI visibly renders raw status/stage text. Review states are `machine-unreviewed`, `in_review`, `changes_requested`, `validated`, `approved`, and published output is an immutable snapshot. Result semantics distinguish `pass`, `fail`, `warning`, `unknown`; applicable/not-applicable; and measured/not-measured/collection-failed.

## Recommended writing guidance

Use concise, factual, action-oriented language. For a user-facing finding, present **observation**, **evidence**, **impact**, then **recommendation** where the report payload supports those fields. Describe inferred or visual-model output as probabilistic; identify incomplete collection or unavailable measurement rather than treating it as a pass.

For errors, state what happened and the safe next action without exposing stack traces, credentials, or internal paths. Prefer action labels already present in the UI: **Start audit**, **Cancel audit**, **Save revision**, **Validate**, **Approve**, and **Publish reviewed report**. The current raw `Finding changes (structured JSON)` field is accurate but technical; guided copy/control design is recommended, not implemented.

Avoid unsupported wording including “fully accessible,” “WCAG compliant,” “guaranteed,” “complete site audit,” “field Core Web Vitals,” or “100% coverage.” Scores should be described as measured evidence-aware results; calibration and KPI approval remain unresolved.
