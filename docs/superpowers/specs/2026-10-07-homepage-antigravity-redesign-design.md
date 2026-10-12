# Homepage Antigravity Redesign — Design

Date: 2026-10-07 · Branch: feat/quick-audit · Status: approved in brainstorming, pending spec review

## Intent

**What the user asked for**
- Redesign the landing page (`/`, `src/ui/frontend/landing/Landing.jsx`) after the structure and motion of antigravity.google, without its video.
- One visual language with the client report cover restyled on 2026-10-07 (`c3847fb`): light canvas, oversized tightly tracked headline, dot field in EY yellow / purple / grey, pill chips. Motion lives on the homepage only; the report stays static.

**Decisions taken**
- Audience: both prospective clients (marketing + SEO) and colleagues using the shared link. The page must sell the service and keep a one-click route into `/app`.
- Hero motion: an interactive canvas dot field that drifts and parts around the cursor (option A).
- Structure: restage the current content and add a pinned "How it works" section (option B). The 3 benefit cards are folded into its steps.
- Technique: Canvas 2D + CSS `position: sticky` + IntersectionObserver. No new dependency; GSAP (listed in `package.json`, unused) stays unused.

**Success criteria**
- Hero shows the unchanged `h1`, two actions and a moving dot field; with reduced motion the field is a static frame and nothing animates.
- The W3C demo starts when it scrolls into view and finishes with the same 5 findings and 7 axis chips as today.
- "How it works" marks the active step as the user scrolls, and its panel follows; on narrow screens it reads as a plain list.
- No horizontal scroll and a clean axe run at 375, 768, 1024 and 1440 px, in EN and FR.
- JSON-LD, head tags, FR/EN switching and `test_landing_copy.py` keep passing unchanged.

## Out of scope
- Any change to the app (`/app`), the client report or its cover.
- New audiences/use-case sections, blog, testimonials, video.
- A JavaScript unit-test runner.

## Visual language
Landing-scoped CSS variables on `.lp`, copied from `src/report/client/styles.css`: ink `#1F2430`, ink-2 `#3D4456`, muted `#5B6275`, line `#E4E7EF`, canvas `#F7F8FC`, accent `#5B3FD9`, accent-soft `#EFEBFF`, EY `#FFE600`. Dot palette `#5B3FD9`, `#9AA1B5`, `#9AA1B5`, `#E8C300` (same weights as the cover's `_dot_field`). App-wide tokens in other stylesheets are not touched. Font stays Inter.

## Page structure
1. **Header** — logo left; right: FR/EN pill and an "Open the app" link. Transparent over the hero, then sticky translucent white with `backdrop-filter: blur` once the hero has scrolled out.
2. **Hero** (min-height 100svh) — full-bleed `DotField` behind centred text: eyebrow pill with yellow dot, `h1` at `clamp(48px, 8vw, 104px)` / tracking ≈ −0.045em (keeps the dashed "evidence" selection frame), lead, primary "Start an audit" (ink pill → `/app`), secondary "See it work" (outline pill → `#demo`), source chips as pills.
3. **Demo** (`id="demo"`) — current capture + audit log and caption, restyled to the tokens.
4. **How it works** — `h2` title; left column an `<ol>` of 3 steps (large numeral, `h3`, text); right column one sticky panel whose content follows the active step, with a thin accent progress rail. Below 900 px the panel is not sticky and each step shows its own panel inline.
5. **The 7 axes** — current content in white cards; 3 → 2 → 1 columns.
6. **Closing CTA** — one line and "Start an audit" over a static, quieter dot field.
7. **Footer** — the two current lines over an oversized pale "EY Studio+" wordmark, cropped by the page edge, `aria-hidden`.

## Motion
| Element | Behaviour | Reduced motion |
|---|---|---|
| Dot field | Rings around the headline, fading outward; count scales with hero area, max 1,400; DPR capped at 2. Idle drift around home positions; dots within ~140 px of the pointer are pushed away and spring back. Touch: drift only. Entrance: rings fade in centre-out over ~900 ms. Loop runs only while the hero is intersecting and `document.visibilityState === "visible"`. | One static frame, no loop |
| Hero entrance | Eyebrow, `h1`, lead, actions rise 12 px + fade, 600 ms ease-out, 80 ms stagger | None |
| Section reveals (`.lp-reveal`) | Fade + 16 px rise, 500 ms, once; cards stagger 60 ms. Content is visible by default; the hidden start state is applied only after JS confirms IntersectionObserver | None |
| Demo | Scan starts when 40 % visible (today: on mount); Replay unchanged | Finished state immediately (as today) |
| How it works | Step active when it crosses the viewport centre; panel crossfade 300 ms; rail fills 1 → 3. No scroll hijacking | Instant switch |
| Header | Transparent → translucent after hero | Same, no transition |

## Copy
Unchanged: `h1`, eyebrow, lead, source chips, demo copy and caption, 7 axes, footer lines, head tags, JSON-LD. Removed: `benefits`, `benefitsLabel`. New keys (EN / FR), all in `COPY` in `Landing.jsx`:

| Key | EN | FR |
|---|---|---|
| openApp | Open the app | Ouvrir l’application |
| seeIt | See it work | Voir l’audit en action |
| howTitle | How every audit is built | Comment chaque audit est construit |
| step 1 | **Capture every screen.** Point it at a URL, screenshots, an Android app or a Figma file. It records each screen and the elements on it. | **Capturer chaque écran.** Indiquez une URL, des captures, une app Android ou un fichier Figma. L’outil enregistre chaque écran et ses éléments. |
| step 2 | **Check 7 axes, {CRITERIA_TOTAL} criteria.** Automated tools measure what can be measured; the AI agent reviews the rest and keeps a finding only with 80% confidence and cited evidence. Each axis is scored out of 100. | **Vérifier 7 axes, {CRITERIA_TOTAL} critères.** Les outils automatisés mesurent ce qui est mesurable ; l’agent IA examine le reste et ne retient un constat qu’avec 80 % de confiance et une preuve citée. Chaque axe est noté sur 100. |
| step 3 | **A specialist signs off.** Every finding is reviewed before the report is published, in the app, as a shareable link and as a PDF. | **Validé par un spécialiste.** Chaque constat est relu avant publication : dans l’application, en lien partageable et en PDF. |
| closing | See the evidence behind your product’s UX. | Voyez les preuves derrière l’UX de votre produit. |

`{CRITERIA_TOTAL}` is the computed constant (67 today), never a literal. Product copy never says "Claude", "VLM" or "machine finding".

Panel content per step: 1 Capture — W3C thumbnail with element outlines; 2 Check — the 7 axis chips and the "Coverage 85%" meter; 3 Sign-off — `select · WCAG 4.1.2 · axe-core` tag and Draft → Saved → Deployed.

Headings: one `h1`; `h2` per section; `h3` per step. The step list is a real `<ol>`; the active step carries `aria-current="step"`.

## Units
| File | Responsibility | Interface |
|---|---|---|
| `landing/Landing.jsx` | Page composition, `COPY`, `AXES`, head tags, JSON-LD | default export `Landing` (unchanged) |
| `landing/DotField.jsx` | Canvas render loop, pointer repulsion, pause/resume, static frame | default `DotField({ variant: "hero" \| "quiet" })`; named `buildField(width, height) → [{ x, y, r, color, alpha }]` (pure) |
| `landing/HowItWorks.jsx` | Steps, active-step tracking, sticky panel | default `HowItWorks({ lang, t })` |
| `landing/useInView.js` | One IntersectionObserver wrapper | `useInView(options) → [ref, inView]` |
| `styles/landing.css` | Rewritten; tokens scoped to `.lp` | — |

`buildField` keeps an elliptical centre zone clear for the headline and returns ≤ 1,400 dots for any size.

## Testing
Playwright, in `tests/test_frontend_browser.py` (browser tests need `npm run build`). Each new assertion is written first and seen failing.

1. Hero: `h1` text unchanged; a `canvas[aria-hidden=true]` is present and has non-blank pixels after 1 s.
2. Demo: status is not "complete" before scrolling; after scrolling `#demo` into view it reaches "UX/UI audit complete"; 5 log rows, 7 axis chips, one "Measured · axe-core".
3. How it works: 3 step `h3`s; scrolling step 3 into the centre gives it `aria-current="step"` and the panel shows "Deployed".
4. Reduced motion (`emulate_media(reduced_motion="reduce")`): demo complete without scrolling; canvas still non-blank; no `.lp-reveal` element left at opacity 0.
5. 375 / 768 / 1024 / 1440: no horizontal scroll, axe clean, screenshot; at 375 the panel's computed `position` is not `sticky`.
6. FR: new copy present, including "Voir l’audit en action".
7. Field limits (the bundle is minified, so test through the DOM, not by importing `buildField`): the canvas exposes `data-dots`; it is ≤ 1,400 at 1440×900 and 3840×2160, and `getImageData` at the canvas centre is fully transparent (centre zone clear).
8. Page text contains none of "Claude", "VLM", "machine finding".

**Changed rule:** the existing assertion "`main` has exactly one link" becomes "every link in `main` points to `/app` or `#demo`, and exactly 2 point to `/app`". The intent — one destination — is kept.

Kept unchanged: `tests/test_landing_browser.py` (JSON-LD), `tests/test_landing_copy.py`, the `/app` round-trip and the FR/EN switch test.

Done means: tests green, and Playwright screenshots at every width inspected by eye before the work is called finished.
