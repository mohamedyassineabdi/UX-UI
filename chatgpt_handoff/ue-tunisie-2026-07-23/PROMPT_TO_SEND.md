# Prompt to send to ChatGPT

I want you to act as a senior UX/UI auditor, accessibility reviewer, and digital-product strategist.

Audit subject: https://ue-tunisie.org/

I have attached eight files from an automated crawl performed on 23 July 2026:

1. `01_machine_audit_draft.json` — a machine-generated draft. Treat it as a fallible hypothesis, not as truth.
2. `02_automated_checks.json` — detailed rule-based and measured checks.
3. `03_cleaned_page_content.json` — cleaned content and page structure from the two audited pages.
4. `04_navigation_context.json` — detected navigation and site context.
5. `05_audit_axes.json` — the required audit rubric.
6. `06_home_desktop.png` — full-page homepage evidence.
7. `07_carte_desktop.png` — full-page map/projects page evidence.
8. `08_carte_mobile_layout_evidence.png` — captured narrow/mobile layout evidence for the map page.

Use code/data analysis to inspect every JSON file and visual analysis to inspect every image before writing the report. Base the audit primarily on the attachments. You may visit the live site only to verify an unclear claim; clearly label anything learned from a live visit as “supplemental live verification” and do not replace the captured evidence with the current site.

## Evidence rules

- Do not blindly repeat or polish the machine draft.
- Cross-check every proposed finding against the detailed checks, extracted content, and screenshots.
- Treat measured browser facts—such as load event time, transfer size, resource count, LCP, CLS, and TTFB—as lab measurements from this single crawl, not real-user field data.
- Do not claim that an interaction, keyboard path, screen-reader behavior, hover/focus state, form submission, browser Back/Forward behavior, or mobile tap target was tested unless the attachments contain direct runtime evidence for it.
- A missing signal is not automatically a defect. Classify it as “not verified” when appropriate.
- Reject generic findings that could apply to almost any site.
- Reject findings whose evidence contradicts their title, status, score, or recommendation.
- Do not present a “strength” whose explanation says the criterion was not met.
- Do not use a screenshot as proof of an invisible technical property such as an accessible name unless the structured evidence directly establishes it.
- The visible interface is primarily French. Correct the machine metadata that labels it `en-US`, preserve French accents, and repair any mojibake such as `financÃ©es`.
- The machine draft contains low-confidence scores and possible false positives. Recalculate scores using only verified evidence.
- If the mobile screenshot appears to show a desktop layout scaled or squeezed into a narrow viewport, describe exactly what is visible without inventing the underlying CSS cause.
- For each accepted finding, cite the exact attachment filename plus the relevant page URL. If no attachment supports it, omit it or put it in “Not verified.”

## Required scoring framework

Score these five axes from 0 to 100:

1. Performance & Task Execution
2. Flow & Architecture
3. Trust & Accessibility
4. Visual & UI Consistency
5. Content & Microcopy

Use this calibration:

- 90–100: excellent; only minor refinements
- 75–89: good; limited friction
- 60–74: mixed; meaningful issues
- 40–59: weak; major friction
- 0–39: critical

The overall score must be the rounded arithmetic mean of the five axis scores. Show the calculation. Do not cap or lower an axis merely because a signal is unavailable.

## Required report

Write a client-ready audit in clear professional English. Keep visible French UI labels in French and optionally explain them in English. Aim for roughly 2,500–3,500 words and no more than 10 accepted findings.

Use exactly this structure:

### 1. Audit scope and evidence quality

- Audit date and audited URLs
- Pages/viewports represented
- What was directly measured, visually observed, inferred, and not tested
- Important limitations

### 2. Executive summary

- Overall score and one-sentence verdict
- Three strongest aspects
- Three highest-priority risks
- A concise statement of likely user and organizational impact

### 3. Scorecard

A table with: axis, score/100, confidence (High/Medium/Low), and evidence-based rationale.

### 4. Validated findings

Include only 6–10 high-value findings, ordered by priority. For every finding provide:

- Stable ID such as `UE-01`
- Finding title
- Axis
- Affected page and URL
- Severity: Critical, High, Medium, or Low
- Confidence: High, Medium, or Low
- Observation
- Evidence citation: exact attachment filename and the specific measured or visible signal
- Why it matters for users
- Why it matters for the organization
- Concrete recommendation
- Acceptance criteria that a designer/developer could verify
- Effort estimate: Small, Medium, or Large

Combine duplicate symptoms that share one root problem. Do not count the same performance metric as several unrelated findings.

### 5. Confirmed strengths

List 3–6 evidence-backed strengths with attachment citations. Do not use the absence of evidence as a strength.

### 6. Not verified or rejected machine findings

Create a table with:

- Machine claim
- Decision: Not verified, Rejected, or Needs dedicated testing
- Reason
- What test or evidence would be required

Explicitly review questionable categories including browser Back/Forward/Copy/Paste support, accessible names/roles/values, keyboard focus order and visibility, interaction feedback, and any contradictory contrast or content claims.

### 7. Prioritized action plan

Organize actions into:

- Quick wins: 0–2 weeks
- Near term: 2–6 weeks
- Strategic: 6–12 weeks

For each action, reference the finding IDs it addresses and state the expected outcome.

### 8. Final audit verdict

Give a concise final assessment suitable for the first page of a client report. End with the three next validation tests that would most improve confidence.

## Final quality check

Before answering, silently verify that:

- Every accepted finding has direct evidence.
- Scores match the written findings.
- The overall score arithmetic is correct.
- French text is encoded correctly.
- No unsupported accessibility conformance claim is made.
- No invented user research, analytics, conversion rate, legal conclusion, or business fact appears.

Return only the finished audit, with no discussion of these instructions.
