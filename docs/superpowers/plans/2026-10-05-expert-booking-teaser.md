# Strategic Roadmap Teaser + Expert Booking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Per the user's preference, this plan is lean: it specifies files, interfaces, behaviours, and test cases, not full code.

**Goal:** Add a blurred, lead-generation "strategic redesign roadmap" section at the end of every report surface, which opens a Cal.com booking modal with the EY Studio+ expert.

**Architecture:** One Python module owns the config, the counts, the copy, and the static HTML rendering. The two Python report renderers (GTM report and reviewed report) call it. The server exposes the same data as JSON for the React report, which renders a matching component. Booking uses a **Cal.com iframe** (`?embed=true`), not Cal's `embed.js`, because `tests/test_frontend_security.py` forbids runtime CDN scripts and an iframe also works in static exported HTML.

**Tech Stack:** Python 3 (stdlib `html`), React (Vite), existing CSS tokens in `src/ui/frontend/styles/tokens.css` / `cx.css`, pytest, Playwright browser tests.

**Spec:** `docs/superpowers/specs/2026-10-05-expert-booking-teaser-design.md`

## Global Constraints

- Default booking URL: `https://cal.com/sofiene-m-hadheb-nwve91/30min`. Env `EXPERT_BOOKING_URL` overrides it; setting it to an empty string disables the section on every surface.
- Expert name: `Sofiene Mhadheb`. Title EN: `Customer Innovation and Experience Design Expert, EY Studio+`. Title FR: `Expert en innovation client et design d'expérience, EY Studio+`. `EXPERT_PHOTO_URL` is optional; without it, show an initials avatar ("SM").
- **No real recommendation or fix text ever appears in the teaser markup, the JSON payload, or `data-*` attributes.** Counts only.
- Only `https://cal.com/...` booking URLs are accepted; anything else disables the section.
- Language: `en` or `fr`; anything else falls back to `en`.
- Section id: `roadmap-teaser`; modal labelled by its heading; Esc closes it and focus returns to the CTA; respects `prefers-reduced-motion`.
- Analytics events: `roadmap_teaser_viewed`, `booking_cta_clicked`, `booking_completed`, pushed to `window.dataLayer` when present (GTM-compatible); otherwise a no-op.

## Review Focus

1. **Report with zero findings** → the section still renders, with counts "0" replaced by copy for a clean audit ("Keep the momentum: plan your next design iteration"). Test in Task 1.
2. **Site URL or report URL with quotes, `<`, or `&`** → escaped in HTML and URL-encoded in the Cal.com `notes` prefill. Test in Task 1.
3. **A non-cal.com `EXPERT_BOOKING_URL` (e.g. `javascript:` or another domain)** → section disabled; never rendered as a link. Test in Task 1.
4. **Iframe fails to load (offline, or the static file opened from disk)** → the CTA remains a real `<a href>` to the booking page with `target="_blank" rel="noopener"`; the modal is a progressive enhancement. Test in Task 4.
5. **Narrow phone width (360 px)** → no horizontal scroll; the modal is full-screen and closable. Test in Task 4.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/report/roadmap_teaser.py` | Config, counts, copy (EN/FR), Cal.com URL building, static HTML + inline CSS/JS |
| `src/gtm_audit/generate_gtm_report.py` | Insert teaser before `<footer class="footer">` |
| `src/report/reviewed_report.py` | Insert teaser before `</body>` |
| `src/ui/server.py` | `GET /api/audits/<id>/roadmap-teaser`; CSP `frame-src` for cal.com when enabled |
| `src/ui/frontend/review/RoadmapTeaser.jsx` | React teaser + booking modal |
| `src/ui/frontend/lib/analytics.js` | `track(event, props)` → `window.dataLayer` |
| `src/ui/frontend/styles/roadmap-teaser.css` | Styles using existing tokens |
| `tests/test_roadmap_teaser.py`, `tests/test_frontend_browser.py` | Tests |

---

### Task 1: Core module — config, counts, copy, static HTML

**Files:**
- Create: `src/report/roadmap_teaser.py`
- Test: `tests/test_roadmap_teaser.py`

**Interfaces — produces:**
- `ExpertBooking(url: str, name: str, title: dict[str,str], photo_url: str | None)` (frozen dataclass)
- `expert_booking_config() -> ExpertBooking | None`: reads env and validates `https://cal.com/` hosts
- `teaser_counts(findings: Iterable[dict]) -> dict[str,int]`, returning keys `quickWins`, `structural`, `axes`:
  - structural = distinct failing findings with severity `critical` or `high`;
  - quick wins = distinct failing findings with severity `medium` or `low`;
  - axes = number of distinct axis ids among the findings;
  - severity is read from `severity` and the axis from `axis` or `axisId`; findings are deduped by `deduplicationId` or `findingId`.
- `teaser_copy(lang: str) -> dict[str,str]`: heading, body, CTA, chips, clean-audit variant, modal title, close label, lock label
- `booking_url(base: str, *, site_url: str, report_url: str | None, embed: bool) -> str`: appends `notes=` (URL-encoded, "Audit: <site> — Report: <url>") and `embed=true` when `embed`
- `teaser_payload(findings, *, lang, site_url, report_url) -> dict | None`: JSON-safe `{counts, copy, expert, bookingUrl, embedUrl}`, or `None` when disabled
- `render_roadmap_teaser_html(findings, *, lang, site_url, report_url=None) -> str`: a self-contained `<section id="roadmap-teaser">`. It holds:
  - scoped `<style>`;
  - 4 skeleton roadmap rows (`aria-hidden="true"`, blurred);
  - a lock badge, the count chips, the expert card, and a CTA `<a href=booking_url(..., embed=False) target="_blank" rel="noopener">`;
  - a `<dialog>` with an `<iframe src=embed_url title=...>` and a close button;
  - a small inline script that intercepts the CTA click to `showModal()` (if `HTMLDialogElement` is supported), handles Esc and focus return, and pushes the dataLayer events.
  - Returns `""` when disabled.

- [ ] Step 1: Tests:
  - env unset → default URL and name;
  - `EXPERT_BOOKING_URL=""` → `None` and `""`;
  - **Review Focus 3:** `javascript:alert(1)` and `https://evil.com/x` → disabled;
  - counts over a fixture mixing severities, duplicate `deduplicationId`s, and passes;
  - **Review Focus 1:** zero findings → the clean-audit copy is present;
  - **Review Focus 2:** a `site_url` containing `"<&` is escaped in HTML and encoded in the URL;
  - sentinel test: findings whose `recommendation` / `fix` / `recommendedFix` fields contain `SENTINEL_FIX_TEXT` → the sentinel is absent from both the HTML and `json.dumps(teaser_payload(...))`;
  - FR copy when `lang="fr"`, EN fallback when `lang="de"`.
- [ ] Step 2: Run `python -m pytest tests/test_roadmap_teaser.py -v`. Expect FAIL.
- [ ] Step 3: Implement. Use `html.escape` for every interpolation; keep CSS to the existing token names with literal fallbacks, since static reports don't load `tokens.css`.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(report): roadmap teaser core with expert booking config`.

### Task 2: Insert the teaser into both static report renderers

**Files:**
- Modify: `src/gtm_audit/generate_gtm_report.py` (in `render_html`, immediately before `<footer class="footer">`, ~line 3220)
- Modify: `src/report/reviewed_report.py` (`render_reviewed_report`, before `</body>`)
- Test: `tests/test_roadmap_teaser.py`

**Interfaces — consumes:** `render_roadmap_teaser_html` from Task 1. Each renderer passes its own findings list, the report's language (default `en` until sub-project #3 adds selection), and the audited site URL.

- [ ] Step 1: Tests:
  - render the reviewed report from a minimal context fixture and assert `id="roadmap-teaser"` appears exactly once, after the findings and before `</body>`;
  - the GTM report: call `render_html` with the smallest existing fixture used by `tests/test_gtm_axe_scoring.py` (reuse its builder) and assert the teaser sits before the footer;
  - with `EXPERT_BOOKING_URL=""` (monkeypatch) neither output contains the section.
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement the two insertions.
- [ ] Step 4: Run `python -m pytest tests/test_roadmap_teaser.py tests/test_gtm_axe_scoring.py tests/test_frontend_security.py -q`. Expect PASS; this includes `test_report_generators_submit_no_html_payload`.
- [ ] Step 5: Commit `feat(report): add roadmap teaser to exported reports`.

### Task 3: Server endpoint and CSP

**Files:**
- Modify: `src/ui/server.py` (route registration next to the existing audit routes; CSP header at ~line 1583)
- Test: `tests/test_roadmap_teaser.py` (follow how `tests/test_frontend_data_contracts.py` starts the server or calls handlers)

**Interfaces — produces:** `GET /api/audits/<id>/roadmap-teaser?lang=en|fr` → `200 {counts, copy, expert, bookingUrl, embedUrl}` when enabled, or `200 {"enabled": false}` when disabled. It uses the same auth as the other audit routes. `404` for an unknown audit.

**CSP:** when enabled, add `frame-src https://cal.com https://app.cal.com`. When disabled, the CSP is unchanged.

- [ ] Step 1: Tests:
  - authenticated request → 200 with counts and no sentinel text;
  - unauthenticated → same status as other audit routes;
  - unknown id → 404;
  - CSP contains `frame-src https://cal.com` only when enabled;
  - `script-src` is unchanged (still no third-party script).
- [ ] Step 2: Run. Expect FAIL.
- [ ] Step 3: Implement. Findings come from the same machine-audit source `InteractiveReport` uses.
- [ ] Step 4: Run. Expect PASS.
- [ ] Step 5: Commit `feat(server): roadmap teaser endpoint and cal.com frame CSP`.

### Task 4: React teaser, booking modal, analytics, browser tests

**Files:**
- Create: `src/ui/frontend/review/RoadmapTeaser.jsx`, `src/ui/frontend/lib/analytics.js`, `src/ui/frontend/styles/roadmap-teaser.css`
- Modify: `src/ui/frontend/review/InteractiveReport.jsx` (render `<RoadmapTeaser api={api} auditId={auditId} />` after the `report-content` section); import the CSS where the other review styles are imported
- Modify: `src/ui/frontend/api/audits.js` (add `getRoadmapTeaser(api, auditId, lang)`)
- Test: `tests/test_frontend_browser.py`

**Interfaces:**
- Consumes: the Task 3 endpoint.
- Produces: `track(event: string, props?: object): void`.

**UI behaviour:**
- **Visual:** mirrors the static version — blurred skeleton rows, a lock badge, count chips, the expert card (initials avatar), and one primary CTA styled as the existing `Button` primary variant.
- **Viewed event:** `IntersectionObserver` fires `roadmap_teaser_viewed` once.
- **CTA:** a real `<a>` to `bookingUrl`. The click handler prevents default and opens a modal (existing dialog pattern if `Primitives.jsx` has one; otherwise a native `<dialog>`) with an iframe at `embedUrl`, and fires `booking_cta_clicked`.
- **Booking completed:** a `message` listener accepts events only from origin `https://cal.com` / `https://app.cal.com` whose data type contains `bookingSuccessful`, and fires `booking_completed`.
- **Hover:** blur 8 px → 6 px plus a 2 px lift over 200 ms ease-out; none under reduced motion.
- **Disabled endpoint:** renders nothing.

- [ ] Step 1: Browser tests, following the `complete()` fixture pattern already in the file:
  - the teaser is visible at the end of `/report`, showing the counts;
  - the page text contains no recommendation text from the fixture findings;
  - clicking the CTA opens the dialog with an iframe whose `src` starts with the booking URL and includes `embed=true`;
  - Esc closes it and focus returns to the CTA;
  - **Review Focus 4:** the CTA `href` is the non-embed booking URL with `target="_blank"`;
  - **Review Focus 5:** at 360 px width, `document.documentElement.scrollWidth <= 360` and the dialog close button is visible;
  - an axe scan of the teaser and the open dialog has no violations;
  - with the section disabled, `#roadmap-teaser` is absent.
- [ ] Step 2: Run `python -m pytest tests/test_frontend_browser.py -k roadmap -v`. Expect FAIL.
- [ ] Step 3: Implement the components, the API helper, and the CSS; rebuild the frontend per `package.json` scripts.
- [ ] Step 4: Run `python -m pytest tests/test_frontend_browser.py tests/test_frontend_security.py -q`. Expect PASS.
- [ ] Step 5: Update `docs/DESIGN-SYSTEM.md` (teaser pattern), `deploy/ux-ui-auditor.env.example` (the 3 `EXPERT_*` vars), and `docs/CONFIGURATION.md`. Commit `feat(ui): roadmap teaser with expert booking modal`.
