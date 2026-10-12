# Client Report Redesign + PDF Export — Design

Date: 2026-10-06 · Branch: feat/quick-audit · Status: approved in brainstorming, pending spec review

## Intent

**What the user asked for**
- The current report (`/report/:id`, React `InteractiveReport`) reads like an internal tool: dense loose text, two nested scroll panes, debug fields (evidence IDs, `measurement_class`) on the main surface. It must meet a Big 4 / EY Studio+ deliverable standard.
- Modern, consulting-grade presentation with charts (inspirations: score gauge, colour-coded principle bars, KPI tiles, Strength / Critical-improvement panels, issue cards pairing a screenshot with Problem / Recommendation).
- Screenshots must show the affected section, not the whole page.
- Never mention "Claude" in product copy; say "the AI agent".
- Downloadable PDF with the same look, sent to clients as a go-to-market tool.
- Visual identity: EY Studio+ logo, modern colours, modern light gradient background.

**Decisions taken**
- The client report is split from the reviewer workspace. Review / Edit stays the auditor's tool; the client report is read-only.
- Approach A: one server-rendered, self-contained HTML client report is the single source of truth for the in-app view, the deployed link, and the PDF.

**Success criteria**
- An audit with ≥10 findings produces a client report whose first two pages communicate overall score, axis scores, severity mix and top priorities without reading prose.
- Every finding card with a `visualRegion` shows a cropped, highlighted screenshot; no card shows a whole-page thumbnail.
- The PDF and the deployed page render from the same HTML; the PDF has selectable text, no clipped cards, and page breaks between sections.
- The string "Claude" appears nowhere in client report output or the AI-review banner.

## Out of scope (separate specs)
- **Sub-project 2 — element-level crawl crops:** recording element bounding boxes at crawl time so axe/deterministic findings (selector only, no region) get precise crops.
- Redesigning the Review / Edit workspace itself.
- Retiring `generate_gtm_report.py` for the CLI pipeline (`npm run report:gtm`); only the web app's publish path switches renderer.

## Architecture

New package `src/report/client/`, small focused units:

| Unit | Responsibility | Depends on |
|---|---|---|
| `context.py` | `build_client_report_context(machine, revision, audit_id)` → plain dict: site, date, executive KPIs, axes, severity counts, strengths/improvements/opportunities, priorities, roadmap buckets, findings (with reviewer edits applied, suppressed removed), appendix data. Pure, no I/O. | `reviewed_report_context` logic (moved/reused) |
| `crops.py` | `crop_evidence(finding, artifacts_root) -> data URI or None`: crops the screenshot to `visualRegion` with padding, draws the highlight box, downsizes, encodes JPEG/WebP as a data URI. Reuses `_visual_region_from_item`, `_region_to_pixels`, `_draw_red_highlight`, `_desktop_crop_box` (imported from `generate_gtm_report.py` as-is; no move, the legacy CLI keeps working untouched). No region → `None` (no image, never full page). | Pillow |
| `charts.py` | Pure functions returning inline SVG strings: `score_gauge`, `axis_bars`, `severity_donut`, `kpi_tile`. Vector, print-safe, no JS. | — |
| `render.py` | `render_client_report(context) -> str`: one self-contained HTML document (inline CSS + inline SVG + data-URI images, no external requests except optional Google Font with system fallback). All text HTML-escaped. | charts, crops output in context |
| `styles.css` (inlined at render) | Tokens, light gradient background, screen layout, `@media print` + `@page` rules. | — |
| `pdf.py` | `render_pdf(html: str) -> bytes` via Playwright Chromium `page.set_content` + `page.pdf(format="A4", print_background=True, prefer_css_page_size=True)`. | playwright (existing dep) |

`reviewed_report.py` keeps `reviewed_report_context` (used by tests/server) but `render_reviewed_report` delegates to `render_client_report`.

## Report structure (screen = PDF, A4 portrait)

1. **Cover** — EY Studio+ logo (`ey_studio_logo_svg`), "UX/UI Audit Report", client site name + URL, audit date, review status line ("Machine audit — not reviewed" / "Reviewed by EY Studio+"), large overall score gauge with rating.
2. **Executive summary** — KPI tile row (overall score /100 + rating, pages audited, total findings, critical blockers); positioning hook as a lead paragraph (max ~3 lines); Top 3 priorities as numbered cards.
3. **Scorecard** — horizontal bar per axis (0–100, colour by band: red < 50, amber 50–69, green ≥ 70, grey "Not scored"); severity donut (Critical/High/Medium/Low) with legend counts; strongest / weakest axis callouts.
4. **Insight panels** — 2×2 grid: Strength areas · Critical improvement areas · Other opportunities · Recommendations (bulleted, max 4 each, from axes `strengths` / `painPoints` / `opportunities` and `recommendations`).
5. **Findings** — grouped by severity (Critical → Low), one card each: severity pill + axis tag + page; title; cropped highlighted screenshot (left) and **The problem** / **Why it matters** / **Recommendation** (right); reviewer note if present. Cards use `break-inside: avoid`.
6. **Roadmap** — recommendations bucketed Now (critical/high) / Next (medium) / Later (low) as three columns.
7. **Appendix** — methodology, coverage (pages scanned list), limitations, per-finding provenance table (ID, source, WCAG criterion, selector). This is the only place debug fields appear.

Copy rules: plain business language; no "Claude", "VLM", "machine finding", raw enum values (`standards_automated`) outside the appendix; AI-discovered findings labelled "Identified by the AI agent".

## Visual system

- Background: soft light gradient (off-white → pale lavender/blue mesh) on screen; flattened to white with a subtle header band in print to save ink and avoid banding.
- Ink: charcoal `#1F2430`; EY yellow `#FFE600` reserved for the logo and one highlight accent (score gauge ring / cover rule), never for text.
- Semantic: Critical `#C62828`, High `#E65100`, Medium `#F9A825`, Low `#2E7D32`; score bands as above. Each colour paired with a text label (no colour-only meaning).
- Type: Inter (Google Fonts) with system-ui fallback; 11pt body in print, clear H1/H2/H3 scale, tabular numerals for scores.
- Cards: white, 12px radius, hairline border, soft shadow on screen only.

## Integration / data flow

```
gtm_audit.json + review revision
  → build_client_report_context (+ crop_evidence per finding)
  → render_client_report → HTML string
      ├─ GET /api/audits/{id}/client-report            (in-app view; latest saved revision or machine-only)
      ├─ snapshot index.html (existing _machine_report_context path → Deploy report, hash integrity unchanged)
      └─ GET /api/audits/{id}/client-report.pdf        (render_pdf; Content-Disposition: attachment; "<site>-ux-audit-<date>.pdf")
```

- Both new routes require `_require_owned_job`, same as `review-report`.
- Frontend: `/report/:id` gains a **Client report** tab (default) that shows the HTML in a sandboxed `<iframe srcdoc>` (fetched with auth) and a **Download PDF** button; the existing View / Review-Edit UI becomes the **Review** tab. Toolbar keeps Deploy.
- `AuditResults.jsx` AI-review banner copy → "The AI agent is reviewing the screenshots. Its findings will be added to the report in about a minute."

## Error handling

- Missing/unreadable screenshot or invalid region → card renders without image (never a broken image, never full page).
- Axis with `scored: false` → grey bar labelled "Not scored" (matches existing radar fix).
- Missing executive summary fields → tile shows "—"; section omitted when it has no content.
- PDF: Playwright launch failure → 503 JSON `{"error": "PDF export is temporarily unavailable."}`; frontend shows inline error, client report still viewable. Render timeout 60 s.
- Untrusted text (page titles, evidence) always escaped; no script in the output document.

## Testing

- `tests/test_client_report_context.py` — fixture audit JSON (+ revision with an edit and a suppression) → KPIs, severity counts, roadmap buckets, suppressed finding absent, edits applied.
- `tests/test_client_report_crops.py` — region crop returns data URI of expected aspect; no region → `None`; missing file → `None`.
- `tests/test_client_report_render.py` — all 7 section landmarks present; no "Claude"/"VLM"/`standards_automated` outside appendix; output escapes injected `<script>`; no external `src=` except fonts.
- `tests/test_client_report_pdf.py` (marked browser) — PDF bytes start `%PDF`, ≥ 3 pages, extractable text contains site name.
- Server route tests: ownership enforced on both routes; PDF content type + disposition.
- Update `tests/test_frontend_browser.py`: Client report tab default, Download PDF triggers request, banner copy says "AI agent".
