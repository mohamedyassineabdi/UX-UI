# Accessibility

**Status:** Implemented-control and gap inventory; not a compliance statement
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Frontend engineers, UX specialists, and accessibility reviewers
**Scope:** UX/UI Auditor application and generated-report markup; target-site Axe findings are separate audit output.
**Related documents:** [UX Specification](UX-SPECIFICATION.md), [Design System](DESIGN-SYSTEM.md), [Security](SECURITY.md), [Product Specification](PRODUCT-SPECIFICATION.md).

## Current application controls

| Area | Implemented evidence | Current gap / limit |
| --- | --- | --- |
| Document/page structure | Frontend source declares `lang="en"`; app uses `main`, header, ordered headings, sections, lists, native buttons/links. | No skip link or navigation landmark in the small launcher. |
| Forms | Visible label wrappers, required/type inputs, select controls, accepted image types, and disabled busy submit button. | No inspected `aria-describedby` help/error association or fieldset/grouping. |
| Errors/review | Top-level error uses `role="alert"`; review textarea has `aria-label`; native buttons support keyboard activation. | Progress/review loading lacks a live-region contract; raw JSON authoring is difficult to validate accessibly. |
| Links/media | External result links use `rel="noreferrer"`; reports generate image alt text and canvas aria labels. | Report/application coverage has not been evaluated as a complete accessibility audit. |
| Visual/motion | Dark color scheme and native controls are styled. | No explicit focus rule, contrast verification, reduced-motion media query, or application responsive breakpoint is implemented in inspected CSS. |

## Audited product versus this application

Website audits can run Axe and other evidence-backed checks against audited websites. That capability does not establish the accessibility of the UX/UI Auditor application, does not certify an audited product, and does not provide a complete accessibility audit. Lighthouse is laboratory data, not field Core Web Vitals.

## Recommended / not current behavior

Prioritize visible keyboard focus, live announcements for progress/errors, explicit form help/error relationships, reduced-motion handling for generated reports, and targeted manual/assistive-technology testing. Verify contrast and responsive interaction before adopting compliance language. No WCAG certification or compliance claim is made by this document.
