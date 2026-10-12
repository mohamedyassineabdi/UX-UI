# Design System

## Visual design pass 4 — CX Platform alignment

The application now uses the CX Platform design system: white panels on a cool grey page (#f6f7fb), slate text and borders, and the EY palette (gold, navy, yellow) for emphasis rather than decoration. Tokens live in `styles/tokens.css`; the component layer is `styles/cx.css`, loaded last so it overrides the earlier glass rules in `liquid.css` without removing them.

- **Actions:** pill buttons. Primary is solid ink (#111827) with white text; secondary is white with a slate-200 border. Dark CTAs lift by 1px on hover (not under reduced motion). Disabled is 50% opacity.
- **Chrome:** the floating top bar is a white/95 band with a slate-200 border and a light blur. The active nav item is navy. A yellow dot sits beside the EY mark.
- **Selection:** the selected source card gets a gold top bar and a raised shadow; the selected finding and active tab use a deep-gold indicator. Selection never depends on colour alone (checkmark, inset bar, text weight).
- **Inputs:** rounded 12px, slate-200 border, deep-gold border plus a soft gold ring on focus.
- **Labels:** field labels and eyebrows use the uppercase tracked style; eyebrows are deep gold.
- **Status:** light ground, darker text and a matching border (emerald, rose, amber, sky). Never a saturated fill.
- **Numbers:** scores, counts and coverage use `tabular-nums`.

**Accessibility deviation from CX:** `ey-gold` (#C5A04F) is only 2.5:1 on white, below the 3:1 needed for focus indicators and state markers and the 4.5:1 needed for text. Gold is therefore decorative only (card top bar, progress bar, focus halo). Eyebrows, focus outlines and selection indicators use `ey-gold-deep` (#8A6D00, 4.9:1). Hint and placeholder text use slate-500 rather than slate-400.

**Font:** Inter first in the stack with system fallbacks. It is not loaded from Google Fonts, because the server CSP is `default-src 'self'`. Self-host the font files if Inter must render everywhere.

**Implemented:** 2026-10-05 · Application only; generated reports retain their own styles.

## Landing page and routes

`/` is the landing page (`landing/Landing.jsx`, `styles/landing.css`); the tool lives at `/app`; reviewed reports at `/report/:id`. The brand mark links home from every page and the report's back link returns to `/app`.

The landing has one hero and one action: **Start an audit** → `/app`, where the source is chosen. A row of 3D source icons under it previews that next step.

The hero is a **UX/UI audit of a real page**: a capture of W3C's Before-and-After Demonstration (inaccessible version, taken from the Internet Archive because w3.org sits behind a bot check). The demo shows one finding per UX dimension, each labelled with its source. The accessibility contrast result (3.88:1 against 4.5:1) is measured by axe-core 4.11 (`landing/assets/w3c-bad-axe.json`); the task, navigation, hierarchy and content findings are expert observations of what is visible in the capture.

A gold scan line sweeps the capture once (about 3.6s, under the WCAG 2.2.2 five-second limit). Each finding's box lands on its element as the line passes, its dimension chip lights up and its row appears in the audit log beside the capture (never on top of it). The log ends with "5 of 5 dimensions checked" and **Replay**. Reduced motion shows the finished state immediately.

The EY Studio+ logo (`assets/ey-studio-plus.png`) is used in the landing header and the app shell.

Below the hero, three benefit cards (Proof for every finding, Scores you can trust, A specialist signs off) each pair a 3D icon with a small proof of what the claim looks like in the tool.

**3D icons** (`components/Icon3D.jsx`): clay-style tiles with a gradient body, extruded base, top highlight and soft shadow. They are used for the four sources (also on the setup cards) and the three benefits. The Figma tile carries the official Figma mark, unaltered.

Text on the gold tint uses `--ey-gold-ink` (#745b00, about 5.5:1); `ey-gold-deep` on that tint is only about 4.5:1.

## Roadmap teaser and expert booking

Every report ends with a lead-generation card (`review/RoadmapTeaser.jsx` in the app; `src/report/roadmap_teaser.py` in exported reports). Both read one stylesheet, `styles/roadmap-teaser.css`, so the surfaces cannot drift.

- Navy card, gold eyebrow, yellow primary CTA (navy text) — the one high-emphasis action on the page.
- Left: blurred placeholder roadmap rows with a centred lock badge. Placeholders are abstract shapes; **no recommendation text is ever in the DOM or API payload**.
- Right: heading, one-line value, count chips (singular/plural EN/FR), expert card, CTA.
- CTA is a real new-tab link to Cal.com; with `<dialog>` support it opens a modal whose Cal.com iframe loads only on click. Esc/backdrop/Close dismiss it and focus returns to the CTA.
- Motion: 200 ms blur-lift on hover, 220 ms dialog entrance; none under `prefers-reduced-motion`.
- Events (`window.dataLayer` when present): `roadmap_teaser_viewed`, `booking_cta_clicked`, `booking_completed`.

## Point of view

A specialist should understand a measurement before trusting a recommendation. The signature is a dimension ledger pairing score and measurement coverage, followed by a finding browser where captured evidence leads the reading order. Content provides visual richness; there is no decorative imagery, gradient dashboard or KPI-card grid.

Apple Design skill improvement guidance informs hierarchy, progressive disclosure, predictable feedback and adaptable split views. This remains a web application with native HTML controls, authored SVG icons and browser conventions. The user-requested appearance selector is retained; Apple fonts, symbols and platform chrome are not copied.

## Tokens and type

Semantic colors live in tokens.css (light only). Contrast is against the white reading surface.

| Role | Token | Value | Contrast on #ffffff |
| --- | --- | --- | --- |
| Content | `--text-primary` | #0f172a slate-900 | 17.9:1 |
| Secondary text | `--text-secondary` | #475569 slate-600 | 7.6:1 |
| Hint / meta | `--text-tertiary` | #64748b slate-500 | 4.8:1 |
| Primary action | `--accent` | #111827 ink (white text) | 17.7:1 |
| Focus / selection / eyebrow | `--focus`, `--accent-indicator` | #8a6d00 ey-gold-deep | 4.9:1 |
| Error | `--color-danger` | #be123c rose-700 | 6.3:1 |
| Warning | `--color-warning` | #b45309 amber-700 | 5.0:1 |
| Success | `--color-success` | #047857 emerald-700 | 5.5:1 |
| Info | `--color-info` | #0369a1 sky-700 | 5.9:1 |

Body is .9375rem (15px), metadata .8125rem, eyebrows and field labels 11px bold uppercase, audit titles a 1.5–1.875rem clamp. Short machine IDs/data use the system monospace stack. Reading passages are limited to about 65–70ch.

Spacing uses 4/8/12/16/24/32/48/64px. Buttons and badges are pills; inputs and panels use 12px corners; featured surfaces 16px. Controls are at least 44px high; fields 46px. Borders organize data and selection; opaque surfaces carry content. Blur is limited to the top bar and sticky review actions, with an opaque reduced-transparency fallback.

## Layout and interaction

The shell allows 1,600px of workspace; setup remains 1,080px. Global navigation sits above local audit tabs. Overview places the dimension ledger beside findings/review distributions; below 900px these stack. Dimension rows reflow at compact widths without shrinking evidence type.

Regular:
```text
Audit identity                         Report / source artifact
Overview | Findings | Review                         Revision state
Findings + search     | Selected finding
Real-field filters   | Captured evidence / provenance
Selected list row    | Machine assessment / review inspector
                     | Next review action + draft state
```

Compact:
```text
Audit identity / outputs
Overview | Findings | Review
Findings list → selected finding
               ← Back to findings
               Evidence → review
               Sticky next action
```

At 768px and above the two reading panes have bounded independent scrolling. Below 768px a single drill-in task fills the width. At 375px source cards form a two-by-two grid and fields stack. Ultrawide screens expand work surfaces while preserving text line limits.

Local tab transitions preserve the browser state. Selecting a different finding resets its reading position. Lists render 25 findings at a time. Sticky review feedback identifies the failed action beside its next action. Optional edits and history use native disclosures.

Motion uses 150ms feedback and 260ms entry. No orchestrated animation is needed for evidence review. Reduced motion disables transitions and indeterminate-bar animation; real stage text remains.

## Component ownership

| Component | Responsibility |
| --- | --- |
| App / AppShell | Current workspace, draft protection, global navigation, theme |
| AuditForm / source components | Compact source configuration, upload/discovery |
| useAuditJob / AuditWorkspace | Polling, cancellation, lifecycle, report loading |
| AuditOverview | Actual score/coverage rows, findings distribution, collection scope |
| FindingBrowser / EvidencePanel | Search/filter/selection, split/drill-in navigation, protected image/provenance |
| GuidedFindingEditor | Schema-aligned human review fields |
| ReviewPanel / useReview / reviewModel | Local sections, authoritative revision state, action ownership, conflicts, validation |
| RevisionHistory | On-demand saved revisions and immutable preview |
| ProtectedResource / api/artifacts | Protected output opening and bounded artifact paths |

Plain React and CSS implement the workspace. No UI, visualization, icon or animation dependency was added.

## Design review references

The installed apple-design references were consulted for principles, accessibility, layout, typography, color, dark mode, materials/Liquid Glass, motion, controls, navigation, loading/feedback, writing and AI/ML transparency.

Applied examples: layout.md › Visual hierarchy, “Use progressive disclosure”; split-views.md › Best practices, “persistently highlight the current selection”; materials.md › Liquid Glass, “Don’t use Liquid Glass in the content layer”; feedback.md › Best practices, “integrating status feedback into your interface”; generative-ai.md › Transparency, “Communicate where your app uses AI.” These are translated into web behavior rather than literal macOS imitation.
