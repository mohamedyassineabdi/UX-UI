# ChatGPT handoff: ue-tunisie.org

This folder contains a focused evidence package for testing how ChatGPT would turn the 23 July 2026 automated crawl into a final client-facing UX/UI audit.

## Recommended workflow

1. Start a new ChatGPT conversation with file/data analysis and image understanding available.
2. Upload the eight files in `files_to_upload/`.
3. Open `PROMPT_TO_SEND.md`, copy everything below its title, and send it after the uploads finish.
4. Do not upload `.env`, logs, caches, or the entire `shared/generated` directory.
5. Return ChatGPT's complete response for comparison with the local report.

## Required uploads

| File | Purpose |
| --- | --- |
| `01_machine_audit_draft.json` | Existing automated synthesis; intentionally treated as a fallible draft |
| `02_automated_checks.json` | Detailed checks and measured signals |
| `03_cleaned_page_content.json` | Page structure and visible content |
| `04_navigation_context.json` | Detected menu and navigation context |
| `05_audit_axes.json` | Scoring/evaluation rubric |
| `06_home_desktop.png` | Full homepage screenshot |
| `07_carte_desktop.png` | Full map/projects screenshot |
| `08_carte_mobile_layout_evidence.png` | Narrow/mobile layout evidence |

## Optional evidence

`optional_evidence/` contains the ten report evidence images produced by this run. They are not needed for the first attempt because most repeat the same underlying pages, and uploading all of them can distract the review. Add a specific optional image only if ChatGPT says that a corresponding claim cannot be resolved from the required files.

## Deliberately excluded

- `rendered_ui_extraction.json` is about 7 MB and contains very verbose low-level extraction data that is largely summarized by the checks and machine draft.
- `html_extraction.json` is superseded for this review by the cleaned content file.
- Generated HTML reports are presentation output, not independent evidence.
- Historical screenshots and audit runs belong to other sites or older tests.
- Secrets and environment configuration are never required for a ChatGPT review.

## Known review traps

- The site is visibly French, but one generated metadata field says `en-US`.
- Some machine text contains mojibake.
- Several machine findings treat unavailable evidence as a failure.
- Some strengths and explanations contradict one another.
- Technical accessibility claims need structured/runtime evidence; screenshots alone are insufficient.
- Performance values are one lab crawl, not field-user data.
