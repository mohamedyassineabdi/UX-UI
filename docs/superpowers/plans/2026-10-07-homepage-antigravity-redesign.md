# Homepage Antigravity Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native, as set in CLAUDE.md) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the landing page (`/`) in the light Antigravity-style language of the report cover, with an interactive dot field, scroll-started demo and a pinned "How it works" section.

**Architecture:** `Landing.jsx` keeps composition, copy and head tags; motion lives in three small units (`DotField.jsx`, `HowItWorks.jsx`, `useInView.js`). `landing.css` is rewritten with tokens scoped to `.lp`. Canvas 2D + CSS sticky + IntersectionObserver, no new dependency.

**Tech Stack:** React 18, Vite 6, plain CSS, Playwright (Python) browser tests.

**Spec:** `docs/superpowers/specs/2026-10-07-homepage-antigravity-redesign-design.md`

## Global Constraints
- No new dependency; GSAP stays unused.
- No `innerHTML` / `dangerouslySetInnerHTML` / `contenteditable` in any `.jsx` (`tests/test_review_ui_contract.py`).
- Copy never says "Claude", "VLM" or "machine finding". `CRITERIA_TOTAL` is computed, never the literal 67.
- Tokens on `.lp` only: ink `#1F2430`, ink-2 `#3D4456`, muted `#5B6275`, line `#E4E7EF`, canvas `#F7F8FC`, accent `#5B3FD9`, accent-soft `#EFEBFF`, EY `#FFE600`. Dot palette `#5B3FD9`, `#9AA1B5`, `#9AA1B5`, `#E8C300`. Font stays Inter. App-wide tokens untouched.
- Headings: one `h1`, an `h2` per section, an `h3` per step; steps are an `<ol>`; active step has `aria-current="step"`.
- Dot field: ≤ 1,400 dots for any size; DPR capped at 2.
- Sticky needs every ancestor free of `overflow: hidden|auto` — use `overflow-x: clip`. Full-bleed uses `width: 100%`, never `100vw` (scrollbar causes horizontal scroll).
- Unchanged: `/app`, the client report, `tests/test_landing_copy.py`, `tests/test_landing_browser.py`, `COPY` keys other than those listed in the spec.
- Browser tests need `npm run build` first. Commit only files you changed.
- The `ui` fixture opens the context with `reduced_motion="reduce"`; tests of motion call `page.emulate_media(reduced_motion="no-preference")` before `goto`.

## Review Focus
1. **Window resized after load** (rotate phone, drag window) → the field rebuilds to the new size, never stretches, stays ≤ 1,400 dots. Test in Task 5.
2. **Hero scrolled away / tab hidden** → the render loop stops. Test in Task 5 (two `toDataURL()` snapshots 300 ms apart are equal once the hero is off-screen).
3. **Phone where the demo block is taller than the viewport** → a 40 % threshold on the whole figure can never be reached. Observe the capture frame (`.lp-browser`) instead. Test in Task 3 at 375×667.
4. **"See it work" anchor jump** → the demo starts and its top is not hidden under the sticky header (`scroll-margin-top`). Test in Task 3.
5. **Replay after a scroll-started run** → button re-enables, a second run completes. Test in Task 3.

---

### Task 1: Copy and page structure

**Files:**
- Modify: `src/ui/frontend/landing/Landing.jsx`
- Create: `src/ui/frontend/landing/HowItWorks.jsx` (static: step 0 active, no tracking yet)
- Modify: `src/ui/frontend/styles/landing.css` (only what new markup needs to stay readable; full restyle is Task 2)
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Produces: `COPY[lang]` keys `openApp`, `seeIt`, `howTitle`, `steps: [[title, text] ×3]`, `closing`; `benefits`, `benefitsLabel`, `BENEFIT_ICONS`, `benefitProof` removed. `HowItWorks({ lang, t })` default export, rendering `<section class="lp-how" aria-labelledby="lp-how-title">` → `h2#lp-how-title`, `<ol class="lp-how-steps">` of `<li class="lp-how-step">` (numeral, `h3`, `p`, inline `.lp-how-panel`), and `<div class="lp-how-stage">` holding the active step's `.lp-how-panel` plus `.lp-how-rail > b`. Panels: 1 = capture thumbnail (`alt=""`) + 3 outline boxes; 2 = 7 chips in `.lp-how-axes` (not `.lp-dims`) + coverage meter 85 %; 3 = `select · WCAG 4.1.2 · axe-core` code + Draft → Saved → Deployed.
- Page order: header (`.lp-header` with brand, `.lp-lang`, `a.lp-open` → `/app` text `t.openApp`) → `main` → hero (`.lp-hero`: eyebrow pill, h1, lead, `.lp-actions` with `a.lp-cta` → `/app` and `a.lp-ghost` → `#demo`, sources) → `section#demo.lp-demo-section` (h2 visually hidden, `AuditDemo`) → `HowItWorks` → `.lp-axes` → `section.lp-closing` (h2 = `t.closing`, `a.lp-cta` → `/app`) → footer (two lines + `span.lp-wordmark[aria-hidden=true]` "EY Studio+").
- The demo section needs an `h2` (spec: one per section) without new copy: a visually hidden `h2.sr-only` with `t.seeIt`.

- [ ] **Step 1: Write failing tests**
  - Edit `test_landing_page_runs_demo_and_has_one_start_action`: replace `to_have_count(1)` on main links with: hrefs of all `main` links ⊂ {`/app`, `#demo`} (compare `getAttribute('href')`), exactly 2 equal `/app`. Click `get_by_role("link", name="Start an audit").first`.
  - In `test_landing_page_switches_between_english_and_french`: `get_by_role("link", name="Lancer un audit").first` (strict mode; the page now has two).
  - New `test_landing_how_it_works_and_copy(ui)`: 3 `h3` inside `ol.lp-how-steps`; `.lp-how-steps li` first has `aria-current="step"`; header link "Open the app" → `/app`; link "See it work" → `#demo`; text "See the evidence behind your product’s UX." visible; `document.body.innerText` contains none of `Claude`, `VLM`, `machine finding`; then `?lang=fr`: "Voir l’audit en action", "Ouvrir l’application", "Comment chaque audit est construit", "Voyez les preuves derrière l’UX de votre produit." present, same forbidden-word check; step 2 text contains `f"{CRITERIA_TOTAL} critères"` computed in the test from `shared/config/audit_methodology_v3.json`.
- [ ] **Step 2:** `npm run build` then `pytest tests/test_frontend_browser.py -k landing -q` → new/changed tests FAIL.
- [ ] **Step 3:** Implement copy, markup and `HowItWorks.jsx`.
- [ ] **Step 4:** Rebuild; `pytest tests/test_frontend_browser.py tests/test_landing_browser.py tests/test_landing_copy.py tests/test_review_ui_contract.py -q` → PASS.
- [ ] **Step 5:** Commit `Restage the landing page with How it works and a closing call to action`.

### Task 2: Visual language, header states and footer wordmark

**Files:**
- Create: `src/ui/frontend/landing/useInView.js`
- Modify: `src/ui/frontend/styles/landing.css` (rewrite), `src/ui/frontend/landing/Landing.jsx`
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Produces: `useInView({ threshold = 0, rootMargin = "0px", once = false } = {}) → [ref, inView]` — `ref` is a `useRef` object; without `IntersectionObserver` `inView` is `true`; `once` disconnects after the first hit.
- `.lp` full width with `overflow-x: clip`; inner containers `.lp-wrap` (`width: min(calc(100% - 48px), 1120px)`). Header `position: sticky; top: 0`, gets `.is-solid` (translucent white + `backdrop-filter: blur(...)`) when the hero is out of view (`useInView` on the hero, `rootMargin: "-80px 0px 0px 0px"`). Hero `min-height: 100svh`, pulled under the header. h1 `clamp(48px, 8vw, 104px)`, `letter-spacing: -.045em`. Pills for eyebrow, actions, sources. Axes 3 → 2 → 1 columns. Hero entrance: CSS keyframes, 12 px rise, 600 ms, 80 ms stagger, none under reduced motion. `.lp-wordmark` oversized, pale, cropped.

- [ ] **Step 1: Write failing tests** — `test_landing_header_turns_solid_after_hero(ui)`: at top, header lacks `is-solid`; after `#demo` scrolled into view, header has `is-solid` and computed `backdropFilter` contains `blur`. Footer `.lp-wordmark` has `aria-hidden="true"`. Extend the responsive loop to EN and FR: at 375/768/1024/1440 no horizontal scroll, axe clean, screenshot `landing-{lang}-{width}`.
- [ ] **Step 2:** Build, run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Build, run landing tests → PASS.
- [ ] **Step 5:** Commit `Restyle the landing page in the light report-cover language`.

### Task 3: Scroll-started demo and section reveals

**Files:**
- Modify: `src/ui/frontend/landing/Landing.jsx`, `src/ui/frontend/styles/landing.css`
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Consumes: `useInView`.
- `AuditDemo` phases `idle | running | done`: ref on `.lp-browser` with `useInView({ threshold: .4, once: true })`; idle → class `is-idle` (CSS `animation-play-state: paused` on scan, boxes, rows, chips); reduced motion → `done` at once. Replay unchanged. `#demo { scroll-margin-top: 96px }`.
- `Reveal({ as = "div", className, children })` in `Landing.jsx`: class `lp-reveal`, plus `is-pending` only when IO exists, motion allowed and not yet seen (`once`). CSS `.lp-reveal.is-pending { opacity: 0; transform: translateY(16px) }`, 500 ms transition, card children stagger 60 ms.

- [ ] **Step 1: Write failing tests** (all with `emulate_media(reduced_motion="no-preference")`):
  - `test_landing_demo_starts_when_scrolled_into_view`: after load + 1 s, status not "UX/UI audit complete"; scroll `#demo` into view → status reaches it; 5 log rows, 7 `.lp-dims li`, one "Measured · axe-core"; click Replay → status leaves and returns to complete.
  - `test_landing_demo_starts_on_a_phone`: viewport 375×667, scroll `.lp-browser` into view → complete.
  - `test_landing_see_it_work_jumps_to_the_demo`: click "See it work" → complete; `#demo` top ≥ header height.
  - `test_landing_reduced_motion_is_static` (fixture default): demo complete without scrolling; every `.lp-reveal` has computed opacity `1`.
- [ ] **Step 2:** Build, run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Build, run landing tests → PASS.
- [ ] **Step 5:** Commit `Start the landing demo when it scrolls into view`.

### Task 4: How it works tracking and sticky panel

**Files:**
- Modify: `src/ui/frontend/landing/HowItWorks.jsx`, `src/ui/frontend/styles/landing.css`
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Consumes: `useInView`.
- One `useInView({ rootMargin: "-50% 0px -50% 0px" })` per step; the last step reporting `inView` becomes active, otherwise the previous active is kept. Active `li` gets `aria-current="step"`; stage renders the active panel keyed by index (300 ms fade, none under reduced motion); rail `b` uses `transform: scaleY((active + 1) / 3)`.
- ≥ 900 px: two columns, `.lp-how-stage { position: sticky; top: 96px }`, inline panels `display: none`. < 900 px: stage `display: none; position: static`, inline panels shown.

- [ ] **Step 1: Write failing tests** — `test_landing_how_it_works_follows_scroll` at 1440: scroll step 3 `li` to centre (`scrollIntoView({block: 'center'})`) → it has `aria-current="step"`, others don't; `.lp-how-stage` contains "Deployed"; stage computed position `sticky`. At 375: stage computed position `static` and not visible; 3 inline `.lp-how-step .lp-how-panel` visible.
- [ ] **Step 2:** Build, run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Build, run landing tests → PASS.
- [ ] **Step 5:** Commit `Track the active How it works step with a sticky panel`.

### Task 5: Dot field

**Files:**
- Create: `src/ui/frontend/landing/DotField.jsx`
- Modify: `src/ui/frontend/landing/Landing.jsx` (hero + closing), `src/ui/frontend/styles/landing.css`
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Produces: default `DotField({ variant: "hero" | "quiet" })` → `<canvas class="lp-field" aria-hidden="true" data-dots={n}>` filling its positioned parent; named `buildField(width, height) → [{ x, y, r, color, alpha }]`, pure: rings centred on the canvas centre (ring gap 26, dot gap 30, ellipse factor .86 as in `render.py::_dot_field`), alpha fading outward, an elliptical clear zone around the centre sized to the headline, spacing widened when the estimate exceeds 1,400 and a final hard cap at 1,400.
- Behaviour: `ResizeObserver` rebuilds and resizes the backing store (DPR ≤ 2). Hero: entrance fade centre-out over 900 ms, idle drift around home positions, mouse-only repulsion within 140 px with spring back; rAF loop only while the canvas intersects and `document.visibilityState === "visible"`. Reduced motion or `quiet`: one static frame per size (quiet at half alpha).

- [ ] **Step 1: Write failing tests**
  - `test_landing_dot_field_draws_and_moves` (no-preference): `.lp-hero canvas[aria-hidden=true]` present; after 1 s some pixel alpha > 0; pixel at the backing-store centre has alpha 0; two `toDataURL()` 300 ms apart differ while the hero is visible; after scrolling to the footer + 300 ms, two snapshots 300 ms apart are equal.
  - `test_landing_dot_field_limits`: at 1440×900 and 3840×2160, `data-dots` ≤ 1400 and > 0; resize 1440 → 375 → `canvas.width == round(clientWidth * min(devicePixelRatio, 2))` and `data-dots` changed.
  - In `test_landing_reduced_motion_is_static`: hero canvas has a non-transparent pixel.
- [ ] **Step 2:** Build, run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Build, run landing tests → PASS.
- [ ] **Step 5:** Commit `Add the interactive dot field to the landing hero`.

### Task 6: Visual check and full suite

- [ ] `UX_UI_QA_DIR=<scratchpad>/qa` run of the landing tests; open every `landing-*` screenshot (EN/FR × 4 widths) and inspect by eye; also a no-preference screenshot of the hero at 1440. Fix and commit anything off.
- [ ] Full suite to a file in the background, read the tail: `.venv/Scripts/python.exe -m pytest -q`.
- [ ] One independent whole-branch review by a fresh subagent on the most capable model; address findings.
