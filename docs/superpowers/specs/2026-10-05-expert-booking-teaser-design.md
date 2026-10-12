# Strategic Roadmap Teaser + Expert Booking — Design

- **Date:** 2026-10-05
- **Status:** Approved 2026-10-05
- **Related:** `2026-10-05-ux-audit-methodology-v3-design.md` (sub-project #5)

## 1. Goal

Lead generation. The report ends with a blurred "strategic redesign roadmap" teaser that signals expert recommendations exist and invites the client to book a call with an EY Studio+ product design expert. Nothing unlocks inside the tool; the expert delivers recommendations through other channels.

## 2. Surfaces

Both:

- the in-app report page (`src/ui/frontend/review/InteractiveReport.jsx`);
- the exported / shared HTML report (`src/report/` site assets).

## 3. Teaser section

- **Placement:** last section of the report, after all findings.
- **Real, audit-specific counts:** e.g. "3 quick wins · 4 structural changes · 7 axes reviewed", derived from findings (severity × axis). Counts only; no recommendation text.
- **Blurred placeholder rows:** generic skeleton shapes (title bars, chips, timeline). **No real recommendation text is ever present in the DOM or report data.**
- **Lock icon, soft gradient fade, gentle hover lift;** respects `prefers-reduced-motion`.
- **Copy (EN / FR, follows report language):** heading about turning the audit into a redesign that meets business goals; one line on what the session delivers.
- **Expert card:** photo (initials avatar until a photo is supplied), name, title.
- **One primary CTA:** "Book a call with an expert" / « Réserver un appel avec un expert ».

## 4. Booking

- The CTA opens an accessible modal (focus trap, Esc to close, labelled dialog) containing the **Cal.com inline embed** with the expert's live availability in the client's timezone.
- The booking form is pre-filled with the audited site URL and a link to the report.
- Cal.com handles confirmation, reminders, and the video link.
- In the exported static report, if the embed script cannot load, the CTA falls back to opening the Cal.com page in a new tab.

## 5. Configuration

| Key | Value |
|---|---|
| `EXPERT_BOOKING_URL` | `https://cal.com/sofiene-m-hadheb-nwve91/30min` |
| `EXPERT_NAME` | Sofiene Mhadheb |
| `EXPERT_TITLE` | Customer Innovation and Experience Design Expert, EY Studio+ |
| `EXPERT_PHOTO_URL` | Optional; initials avatar if empty |

If `EXPERT_BOOKING_URL` is empty, the section is hidden — never a broken button.

## 6. Tracking

Events: `roadmap_teaser_viewed`, `booking_cta_clicked`, `booking_completed` (from Cal.com's embed event). Hooked into the existing analytics approach in `docs/ANALYTICS.md`.

## 7. Testing

- The teaser renders the counts and contains no real recommendation text.
- The CTA opens the modal; the embed container is present; Esc closes the modal and returns focus to the CTA.
- The section is hidden when `EXPERT_BOOKING_URL` is empty.
- EN / FR copy follows the report language.
- axe: no violations on the teaser or the modal.
- Exported HTML report: the section is present and the fallback link works.
