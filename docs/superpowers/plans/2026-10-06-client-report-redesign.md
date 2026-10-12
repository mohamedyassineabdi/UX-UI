# Client Report Redesign + PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Lean plan by user preference: exact files, interfaces and test assertions; no full code listings. Follow surrounding code idiom (compact Python, `html.escape` everywhere, React one-liners as in `review/`).

**Goal:** One server-rendered, EY Studio+-branded, self-contained HTML client report that powers the in-app Client report tab, the deployed snapshot, and a downloadable PDF.

**Architecture:** New package `src/report/client/` (context → crops → charts → render → pdf). `server._machine_report_context` switches to it, so Deploy snapshots use it unchanged. Two new owner-protected routes serve HTML and PDF; the React report page gains a Client report / Review tab switch.

**Tech Stack:** Python 3.12, Pillow 11.3, Playwright 1.43 (Chromium), React 18 + Vite 6, pytest + pytest-playwright browser tests.

**Spec:** `docs/superpowers/specs/2026-10-06-client-report-redesign-design.md`

## Global Constraints

- Scores in data are 0–100 (`axes[].score`, `executiveSummary.overallScore`); display as `/100`, bands: red < 50, amber 50–69, green ≥ 70, grey "Not scored" when `scored` is false or score is None.
- Severity colours: Critical `#C62828`, High `#E65100`, Medium `#F9A825`, Low `#2E7D32`; always paired with a text label.
- Ink `#1F2430`; EY yellow `#FFE600` only for logo + one accent, never text. Font: Inter (Google Fonts) with `system-ui` fallback.
- Output HTML is self-contained: inline CSS, inline SVG, `data:` images; the only external URL allowed is `fonts.googleapis.com` / `fonts.gstatic.com`. No `<script>`.
- Every untrusted string goes through `html.escape(..., quote=True)`.
- Product copy never contains "Claude", "VLM", "machine finding"; raw enums (e.g. `standards_automated`) appear only inside the Appendix section. AI-discovered findings are labelled "Identified by the AI agent".
- No finding card ever shows a full-page screenshot: no precise region → no image.
- Report context must stay JSON-serialisable and image-free (it is stored as `reportContext` in publication metadata); images are passed to the renderer separately.
- Do not stage unrelated working-tree files (`Landing.jsx`, `landing.css`, `index.html`, `tests/test_landing_copy.py`, `.claude-flow/`, `job`) — another session owns them. `git add` only the files each task lists.

## Review Focus

1. Audit JSON with missing/partial sections (no `executiveSummary`, axes without `strengths`, zero findings) → report still renders; empty sections omitted, tiles show "—".
2. Screenshot path pointing outside the repo, missing, or not an image → card renders with no image; never raises.
3. Hostile text in titles/evidence/reviewer notes (`<script>`, `"><img onerror>`) → escaped in HTML and harmless in the iframe (sandboxed, no scripts).
4. Long content (40+ findings, 600-char evidence, long URLs) → PDF cards don't split mid-card or overflow page width.
5. Revision query param for another audit's revision or garbage → 404, never another owner's data.

---

### Task 1: Client report context

**Files:**
- Create: `src/report/client/__init__.py` (empty), `src/report/client/context.py`
- Test: `tests/test_client_report_context.py`

**Interfaces:**
- Consumes: `src.report.reviewed_report.reviewed_report_context(audit_id=, machine=, revision=)` (existing; returns `completeFindings` with `review` merged, `priorities` with suppressed removed, reviewer meta).
- Produces: `build_client_report_context(*, audit_id: str, machine: dict, revision: dict | None) -> dict` with keys:
  `site {name, url}`, `auditDate` (ISO date from `machine["generatedAt"]`/`coverage` or today), `review {status, label, reviewer...}`,
  `overall {score: float|None, rating: str, reason: str}`, `kpis {pagesAudited:int, findings:int, critical:int, blockers:bool}`,
  `positioningHook: str`, `topPriorities: list[{title, axis, severity, recommendation}]` (max 3),
  `axes: list[{id, name, score: float|None, scored: bool, band: "red"|"amber"|"green"|"none", summary}]`,
  `severityCounts {critical, high, medium, low}`, `strongestAxis`, `weakestAxis`,
  `insights {strengths, improvements, opportunities, recommendations}` (each list[str], max 4, deduped),
  `findings: list[{key, title, severity, axis, pageName, pageUrl, problem, whyItMatters, recommendation, reviewerNote, reviewerPriority, aiDiscovered: bool, screenshotPath, visualRegion, evidenceBundle, provenance{...}}]` sorted critical→low,
  `excluded: list[{title, reason}]` (suppressed findings), `roadmap {now, next, later}` (from `machine["recommendations"]`, bucket by priority critical/high→now, medium→next, else later),
  `appendix {methodology: list[str], coverage: list[{name, url}], limitations: list[str]}`.
- Finding `key` = `findingId|id|deduplicationId`, else `ai-<index>` for `aiDiscoveredFindings`. Findings = `completeFindings` (non-suppressed) + `aiDiscoveredFindings` not already present by `(title, pageUrl)`. Reviewer `reviewedRecommendation` overrides `recommendation`; `priorityOverride` overrides severity.

- [ ] **Step 1: Write failing tests** — build a fixture dict modelled on `shared/audits/726e002dba6f/audit/gtm_audit.json` (5 axes incl. one `scored: False`, 3 dedup findings, 2 AI findings, `recommendations` with Critical/Medium/Low, `executiveSummary`). Assert: `kpis.findings == 5`; `severityCounts` matches; unscored axis has `band == "none"`; 44.4 → `"red"`, 62.5 → `"amber"`, 83.3 → `"green"`; suppressed finding absent from `findings` and present in `excluded` with its reason; `reviewedRecommendation` and `priorityOverride` applied; AI findings have `ai-0`/`ai-1` keys and `aiDiscovered`; roadmap buckets correct; `json.dumps(context)` succeeds; empty machine `{}` returns a context with `overall.score is None`, empty lists, and doesn't raise; input dict not mutated.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_context.py -q` → FAIL (module missing).
- [ ] **Step 3: Implement** `context.py` (pure functions, no I/O). Keep helpers private (`_band`, `_severity`, `_finding_record`).
- [ ] **Step 4: Run** the test file → PASS.
- [ ] **Step 5: Commit** `git add src/report/client/__init__.py src/report/client/context.py tests/test_client_report_context.py && git commit -m "Build the client report context from audit data and review edits"`

### Task 2: Evidence crops

**Files:**
- Create: `src/report/client/crops.py`
- Test: `tests/test_client_report_crops.py`

**Interfaces:**
- Consumes: from `src.gtm_audit.generate_gtm_report` import `ROOT_DIR, _visual_region_from_item, _is_precise_region, _region_to_pixels, _desktop_crop_box, _draw_red_highlight` (read their signatures at lines ~821–1017; reuse, do not move).
- Produces: `crop_evidence(finding: dict, *, root: Path = ROOT_DIR, max_width: int = 1100) -> str | None` (JPEG `data:image/jpeg;base64,...`, quality 82) and `crop_all(findings: list[dict], *, root: Path = ROOT_DIR) -> dict[str, str]` keyed by finding `key`, omitting `None`.
- Rules: resolve `screenshotPath` (absolute or relative to `root`); refuse paths that resolve outside `root` or are symlinks; require `_is_precise_region(...)` true, else `None`; crop with `_desktop_crop_box`, draw highlight via `_draw_red_highlight`, downscale to `max_width`; any exception → `None`.

- [ ] **Step 1: Write failing tests** — create a 1440×3000 PNG in `tmp_path` with Pillow. Assert: normalized region `{x:.1,y:.35,width:.25,height:.1,coordinate_system:"normalized_0_1"}` returns a `data:image/jpeg;base64,` URI whose decoded image width ≤ 1100 and height < 3000 (i.e. cropped, not full page); finding with no region → `None`; missing file → `None`; path outside `root` (`../x.png`) → `None`; a `.txt` file renamed `.png` → `None`; `crop_all` returns only keys with crops.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_crops.py -q` → FAIL.
- [ ] **Step 3: Implement** `crops.py`.
- [ ] **Step 4: Run** → PASS. Also run `python -m pytest tests/test_gtm_report_radar.py -q` to confirm the legacy module is untouched.
- [ ] **Step 5: Commit** `git add src/report/client/crops.py tests/test_client_report_crops.py && git commit -m "Crop finding screenshots to the affected region"`

### Task 3: SVG charts

**Files:**
- Create: `src/report/client/charts.py`
- Test: `tests/test_client_report_charts.py`

**Interfaces:**
- Produces (all return `str` of inline `<svg>` with `role="img"` and `aria-label`):
  `score_gauge(score: float|None, *, label: str, size: int = 180) -> str` (270° arc, band colour, centred number, "—" for None);
  `axis_bars(axes: list[dict]) -> str` (one row per axis: name, track, filled bar width = score%, value label, grey + "Not scored" when unscored);
  `severity_donut(counts: dict[str,int]) -> str` (4 segments + centre total; all-zero → neutral ring with "0");
  `BAND_COLOURS: dict[str,str]`, `SEVERITY_COLOURS: dict[str,str]` (values from Global Constraints).
- No external refs, no `<script>`, labels escaped.

- [ ] **Step 1: Write failing tests** — gauge for 60.2 contains "60" and amber colour; gauge for None contains "—"; `axis_bars` with an unscored axis contains "Not scored" and the axis name escaped (`<b>` → `&lt;b&gt;`); donut for `{critical:0,high:4,medium:8,low:5}` contains "17" and only three coloured segments; all-zero donut doesn't divide by zero; every output parses with `xml.etree.ElementTree.fromstring`.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_charts.py -q` → FAIL.
- [ ] **Step 3: Implement** `charts.py`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add src/report/client/charts.py tests/test_client_report_charts.py && git commit -m "Add print-safe SVG charts for the client report"`

### Task 4: Renderer and visual system

**Files:**
- Create: `src/report/client/render.py`, `src/report/client/styles.css`
- Modify: `src/report/reviewed_report.py` (`render_reviewed_report(context)` → builds nothing new; becomes a thin wrapper: if `context` lacks client keys, it is a legacy reviewed context — keep the function signature but delegate to `render_client_report` via the server path in Task 5; tests that call it directly must still pass)
- Test: `tests/test_client_report_render.py`; keep `tests/test_review_source_formats.py` and `tests/test_review_workflow.py` green

**Interfaces:**
- Consumes: Task 1 context, Task 3 charts, `ey_studio_logo_svg` from `generate_gtm_report`.
- Produces: `render_client_report(context: dict, images: dict[str, str] | None = None) -> str` — full `<!doctype html>` document, `lang` from site language, `<title>` "<site> — UX/UI Audit Report".
- Sections in order, each a `<section id=...>`: `cover`, `executive-summary`, `scorecard` (axis bars + severity donut + strongest/weakest axis callouts), `insights` (2×2 panels), `findings`, `roadmap` (Now / Next / Later columns), `appendix`. Empty sections omitted (except cover).
- Finding card: severity pill (text + colour), axis tag, page name; `<h3>` title; `<figure>` with `images[key]` if present; three labelled blocks "The problem" / "Why it matters" / "Recommendation"; reviewer note and "Reviewer priority: <x>" when set; "Identified by the AI agent" badge when `aiDiscovered`.
- Appendix: methodology, coverage list, limitations, provenance table (key, source, WCAG criterion, selector, measurement class), and "Excluded by reviewer" list with reasons.
- CSS (`styles.css`, read once and inlined): tokens on `:root`; screen background = light mesh gradient (`radial-gradient`s of `#EEF2FF`, `#F5F0FF`, `#FFFBEA` over `#F8F9FC`); cards white, 12px radius, hairline border, soft shadow; max content width 1040px; responsive single column < 720px. `@page { size: A4; margin: 14mm 12mm }`; `@media print`: white background, no shadows, `.finding-card, .kpi, .panel { break-inside: avoid }`, `section { break-before: page }` except cover/first, cover fills page one, `print-color-adjust: exact`.
- `render_reviewed_report(context)`: if `context` has `"overall"` key → `render_client_report(context)`; else build a client context from the legacy keys (`completeFindings`, `priorities`, reviewer) via a small adapter in `context.py` (`client_context_from_reviewed(context) -> dict`, add to Task 1's module here with its own test) and render. Legacy assertions that must keep passing: "Reviewer priority: critical", escaped `&lt;strong&gt;`, suppression reason text ("Duplicate"), `f"{kind} evidence"` finding text.

- [ ] **Step 1: Write failing tests** — using Task 1's fixture context plus `images={"ai-0": "data:image/jpeg;base64,AAAA"}`: all 7 section ids present in order; exactly one `<img` and its `src` starts with `data:`; regex for `src=|href=` finds only `data:`, `#`, finding page URLs (`https?://` in `<a href>` only) and Google Fonts; no `<script`; title containing `<script>alert(1)</script>` appears escaped; the words "Claude", "VLM", "machine finding" absent; `standards_automated` only after `id="appendix"`; "Identified by the AI agent" present; "Excluded by reviewer" lists the suppressed title; context with zero findings omits `id="findings"`. Adapter test: `client_context_from_reviewed(reviewed_report_context(...))` round-trips findings count.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_render.py -q` → FAIL.
- [ ] **Step 3: Implement** `render.py`, `styles.css`, adapter, `render_reviewed_report` delegation.
- [ ] **Step 4: Run** `python -m pytest tests/test_client_report_render.py tests/test_review_source_formats.py tests/test_review_workflow.py -q` → PASS.
- [ ] **Step 5: Commit** `git add src/report/client/render.py src/report/client/styles.css src/report/client/context.py src/report/reviewed_report.py tests/test_client_report_render.py && git commit -m "Render the EY Studio+ client report"`

### Task 5: Server wiring — snapshot + HTML route

**Files:**
- Modify: `src/ui/server.py:479-483` (`_machine_report_context`), GET handler near `:1881` (add route before the `review-report` branch)
- Test: `tests/test_client_report_routes.py` (reuse `api_server, create_audit, request` from `test_server_security`)

**Interfaces:**
- `_machine_report_context(job_id, revision) -> (context, html)`: `context = build_client_report_context(...)`; `images = crop_all(context["findings"])`; `html = render_client_report(context, images)`. Context (image-free) is what's stored in `reportContext`.
- `GET /api/audits/{id}/client-report[?revision=<revisionId>]` → owner only (`_require_owned_job`); if `revision` given, `JOB_STORE.get_revision(id, revision)` must exist else 404; returns `text/html; charset=utf-8` with `Content-Security-Policy: default-src 'none'; img-src data:; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com` and `Cache-Control: no-store`.

- [ ] **Step 1: Write failing tests** — write a fixture `gtm_audit.json` into `server.AuditWorkspace(job_id, server.AUDITS_DIR).gtm_audit`; owner GET returns 200, HTML contains `id="executive-summary"` and the CSP header; other owner (`token-b`) → 404; `?revision=<garbage>` → 404; `?revision=<real>` reflects that revision's `reviewNote`; publishing a snapshot (existing publish flow used in `test_review_workflow.py`) stores `reportContext` that is `json.dumps`-able and contains no `data:image`.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_routes.py -q` → FAIL.
- [ ] **Step 3: Implement** the context swap and route.
- [ ] **Step 4: Run** `python -m pytest tests/test_client_report_routes.py tests/test_review_source_formats.py tests/test_review_workflow.py tests/test_server_security.py -q` → PASS.
- [ ] **Step 5: Commit** `git add src/ui/server.py tests/test_client_report_routes.py && git commit -m "Serve the client report and use it for deployed snapshots"`

### Task 6: PDF export

**Files:**
- Create: `src/report/client/pdf.py`
- Modify: `src/ui/server.py` (route `GET /api/audits/{id}/client-report.pdf[?revision=]`, matched before the HTML route)
- Test: `tests/test_client_report_pdf.py`

**Interfaces:**
- `render_pdf(html: str, *, timeout_ms: int = 60000) -> bytes` — sync Playwright, Chromium headless, `page.set_content(html, wait_until="networkidle")`, `page.emulate_media(media="print")`, `page.pdf(format="A4", print_background=True, prefer_css_page_size=True)`; always closes the browser. Raises `PdfExportError` on any failure.
- Route: same auth/revision rules as Task 5; renders HTML via `_machine_report_context`, then `render_pdf`; `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="<slug(site)>-ux-audit-<YYYY-MM-DD>.pdf"` (slug: lowercase `[a-z0-9-]` only); `PdfExportError` → 503 `{"error": "PDF export is temporarily unavailable."}`.

- [ ] **Step 1: Write failing tests** — `render_pdf` on a rendered fixture report returns bytes starting `b"%PDF"`; page count (`len(re.findall(rb"/Type\s*/Page[^s]", pdf))`) ≥ 3; route returns 200 with `application/pdf` and a disposition matching `r'attachment; filename="[a-z0-9-]+-ux-audit-\d{4}-\d{2}-\d{2}\.pdf"'`; other owner → 404; monkeypatch `render_pdf` to raise `PdfExportError` → 503 with the exact error text. Mark the real-Chromium test like other browser tests in the repo.
- [ ] **Step 2: Run** `python -m pytest tests/test_client_report_pdf.py -q` → FAIL.
- [ ] **Step 3: Implement** `pdf.py` and the route.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add src/report/client/pdf.py src/ui/server.py tests/test_client_report_pdf.py && git commit -m "Export the client report as a PDF"`

### Task 7: Frontend — Client report tab, Download PDF, AI agent copy

**Files:**
- Create: `src/ui/frontend/review/ClientReport.jsx`, `src/ui/frontend/api/clientReport.js`
- Modify: `src/ui/frontend/review/InteractiveReport.jsx`, `src/ui/frontend/audit/AuditResults.jsx:14`, `src/ui/frontend/styles/audit.css` (or the stylesheet that holds `.report-*` rules — grep `report-toolbar`)
- Test: `tests/test_frontend_browser.py` (only add/adjust report tests; this file has another session's uncommitted edits — stage with `git add -p` and include only your hunks)

**Interfaces:**
- `api/clientReport.js`: `clientReportPath(jobId, revisionId?)`, `getClientReportHtml(api, jobId, revisionId) -> Promise<string>`, `downloadClientReportPdf(api, jobId, revisionId) -> Promise<void>` (fetch via `api.request`, read filename from `Content-Disposition`, `URL.createObjectURL` + temporary `<a download>`, revoke after click; non-OK → throw with server `error` text).
- `ClientReport.jsx`: props `{api, job, revisionId}`; renders `<iframe title="Client report" sandbox="" srcDoc={html}>` sized to content (fixed min-height 80vh, full width), loading status, `ErrorAlert` on failure.
- `InteractiveReport.jsx`: tab state `"client" | "review"`, default `"client"`, also honours `?tab=review`; toolbar: tabs "Client report" / "Review", "Download PDF" button (busy label "Preparing PDF…", inline error on failure), existing status badge + Deploy kept. Review tab shows the current intro + FindingBrowser + action bar unchanged. Intro copy drops "Machine analysis" eyebrow in client tab.
- `AuditResults.jsx`: running copy → "The AI agent is reviewing the screenshots. Its findings will be added to the report in about a minute."

- [ ] **Step 1: Write failing browser tests** — opening `/report/{id}` shows tab "Client report" selected and an iframe titled "Client report" whose `content_frame` contains `#executive-summary`; clicking "Download PDF" triggers `page.expect_download()` with suggested filename ending `.pdf`; existing report tests (`test_review_save_and_deploy_from_interactive_report`, `test_report_deploying_state_locks_actions`, `test_completed_overview_opens_local_interactive_report_and_deploys_saved_revision`, `test_interactive_report_blocks_unsaved_deployment_and_keeps_local_revision_on_failure`) navigate with `?tab=review` or click "Review" first; AI review running banner text contains "AI agent" and not "Claude".
- [ ] **Step 2: Run** `npm run build && python -m pytest tests/test_frontend_browser.py -q -k "report or ai_review"` → new tests FAIL.
- [ ] **Step 3: Implement** the components, API helpers, copy and styles (tabs reuse `Button` `is-active` pattern already in the toolbar).
- [ ] **Step 4: Run** `npm run build && python -m pytest tests/test_frontend_browser.py tests/test_frontend_security.py tests/test_review_ui_contract.py -q` → PASS.
- [ ] **Step 5: Commit** `git add src/ui/frontend/review/ClientReport.jsx src/ui/frontend/api/clientReport.js src/ui/frontend/review/InteractiveReport.jsx src/ui/frontend/audit/AuditResults.jsx <stylesheet> && git add -p tests/test_frontend_browser.py && git commit -m "Show the client report in-app with PDF download"`

### Task 8: Visual QA on a real audit + full suite

**Files:** none expected; fix-ups go into the owning task's files with their own commit.

- [ ] **Step 1:** Start the UI (`npm run build && python -m src.ui.server`) and open `/report/726e002dba6f`. Screenshot the client tab at 1440px and 390px widths with Playwright into the scratchpad.
- [ ] **Step 2:** Download the PDF; render pages 1–4 to PNG (`pdftoppm` or Playwright screenshot of the PDF viewer) and inspect: cover fills page 1; KPI tiles + gauge on page 2; no card split across pages; no horizontal overflow; crops show the highlighted region, not a full page; no "Claude".
- [ ] **Step 3:** Fix any defect found (each with a test where it's logic, not pure styling), commit.
- [ ] **Step 4:** Run the full suite `python -m pytest -q` and report the exact pass/fail counts (baseline: 699/700, the 1 failure owned by the landing-page session).
