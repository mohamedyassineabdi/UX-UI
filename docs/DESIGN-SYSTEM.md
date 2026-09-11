# Design System

**Status:** Observed implementation-level design system; not a formal component library
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** Designers and frontend engineers
**Scope:** Current application styles and separately generated report styling.
**Related documents:** [UX Specification](UX-SPECIFICATION.md), [Accessibility](ACCESSIBILITY.md), [Styleguide](STYLEGUIDE.md).

## Maturity and foundations

The React application has a small CSS-variable foundation, local component classes, and no formal token package, Storybook, icon system, or shared component library. `src/ui/frontend/styles/tokens.css` defines a dark `color-scheme`, background `#232332`, surface `#303142`, text `#f7f4ff`, muted `#beb7d5`, primary `#9b63ff`, danger `#ff5c7a`, three spacing tokens (`.5rem`, `1rem`, `1.5rem`), `12px` radius, and one shadow. Its font stack is `Inter, system-ui, sans-serif`.

Generated reports use a separate, more extensive light token set in `src/report/site_assets/styles.css`: backgrounds, ink, panels, yellow/gold accent, success/danger/warning colors, 8/16/24px radii, nine spacing steps, and two shadows. That is report-output styling, not a shared frontend system.

## Layout and components

The application `main` container has `max-width: 980px`, centered margin, and tokenized padding. Cards provide surface, radius, shadow, and margin; actions use wrapping flex layout. The form is a grid; its submit button aligns to start. The current reusable source components are:

| Component | Current states/role | Path |
| --- | --- | --- |
| `AuditForm` | Four audit-type variants; busy submit state | `src/ui/frontend/audit/AuditForm.jsx` |
| `AuditResults` | Terminal result and optional report/artifact links | `src/ui/frontend/audit/AuditResults.jsx` |
| `ReviewPanel` | loading, review status, JSON changes, action buttons, revision history | `src/ui/frontend/review/ReviewPanel.jsx` |
| `App` | page shell, error alert, progress/cancel section | `src/ui/frontend/App.jsx` |

The report renderer separately uses cards, score rings, evidence frames, tabs, screenshots, tables, and reveal/progress animation. It has responsive breakpoints at 1024px, 768px, and 480px. The application CSS contains no media queries; responsiveness is therefore limited to its fluid container/form/flex behavior rather than verified breakpoint design.

## Current inconsistencies and recommendations

**Observed:** the application and reports have separate palettes, spacing scales, radii, and typography definitions. Application focus styling, semantic success/warning colors, explicit motion preferences, and a centralized component API are not implemented in the inspected frontend CSS.

**Recommended / not current behavior:** consolidate documented semantic tokens across app/report surfaces, add visible focus states and reduced-motion handling, define responsive breakpoints for the launcher, and extract repeatable button/status/alert patterns only after product/design approval. These recommendations are not evidence of a current formal design system.
