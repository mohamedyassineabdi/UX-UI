# Codex CLI audit backend (optional)

The UX/UI Auditor can invoke the **locally installed, authenticated Codex CLI**
for its existing AI review and screenshot vision review. This adapter does not
alter audit methodology, scoring, report schemas, or UI.

## Local setup

1. Install a recent Codex CLI and run `codex login` on the machine that runs
   the Python auditor. Check authentication using `codex login status`.
2. Set these variables in your existing local `.env`:

```dotenv
AI_REVIEW_BACKEND=codex_cli
GTM_VISION_BACKEND=codex_cli
# Optional; if omitted, Codex selects its default supported model:
# GTM_CODEX_MODEL=
# AI_REVIEW_MODEL=
# GTM_CODEX_CLI=codex
```

The two backend variables are independent. Select only one if desired.
For AI review, `AI_REVIEW_MODEL` overrides `GTM_CODEX_MODEL`. For screenshot
vision, `GTM_CODEX_MODEL` is used unless the existing call specifies a
model explicitly. Use an image-capable Codex model for the vision backend.

This integration requires no separate OpenAI API key; Codex uses the
authentication of its installed CLI. Subscription usage limits may apply.
Only run this on a trusted machine with an authorized CLI login.

## Security and failure behavior

- Each subprocess executes `codex exec` in a fresh temporary directory with
  `--sandbox read-only`, `--ephemeral`, `--ignore-user-config`,
  `--ignore-rules`, and `--skip-git-repo-check`.
- No shell or API credentials are supplied to the subprocess. Screenshot
  file paths are passed as individual `--image` arguments and no other
  local files are attached.
- The adapter obtains only the last assistant message, discards raw execution
  logs, and passes the response into the **existing Pydantic validation
  gateway**. Invalid JSON receives the existing bounded schema-correction
  attempt; nonzero exit, timeouts, and unavailable CLI fail closed.
- The read-only sandbox prevents model-driven repository edits, but Codex
  runs using the local CLI account and may transmit prompt/image contents
  to its configured model provider. Do not pass confidential evidence without
  authorization. For a stronger threat boundary, use OS/container isolation
  and disable optional account tools/apps at the host policy level.

Without `AI_REVIEW_BACKEND=codex_cli` or
`GTM_VISION_BACKEND=codex_cli`, the existing Groq/OpenAI/Ollama
selection is unchanged.

Run contract checks with:

```bash
pytest -q tests/test_codex_cli_backend.py
```

## Codex-powered navigation recovery

The optional weak-navigation recovery in `navigator/ai_navigation_helper.py`
also uses Codex CLI, replacing its earlier Ollama/LLaMA request. Enable it
for local website audits with:

```dotenv
CRAWLER_USE_AI_NAV=1
USE_AI_NAV=1
CRAWLER_AI_NAV_TIMEOUT_SEC=30
# Optional: CRAWLER_CODEX_MODEL=
```

These flags control **whether** the crawler attempts AI recovery; they do not
change the global LLM or GTM vision backend switches. Navigation recovery is
only attempted if deterministic discovery finds weak navigation; healthy
menus do not consume Codex calls. The CLI receives a viewport screenshot and
a capped list of browser-extracted candidates. A short timeout (5–60 seconds,
30 by default) is constrained by the remaining audit budget. If CLI inference,
schema validation or safety checks fail, discovery keeps the deterministic
result and records an AI-recovery failure.

The model cannot invent a URL or instruct the crawler to click arbitrary
elements. Only a currently listed DOM candidate with a menu-oriented label
and sufficient confidence is eligible. Categories without observed DOM
evidence are filtered. This does not replace the crawler's SSRF, robots,
interaction-safety or destination validation controls.

Run focused checks:

```powershell
uv run pytest -q tests/test_codex_cli_backend.py tests/test_codex_navigation.py
```

After pulling this branch and restarting your local server, repeat a Quick
website audit with these flags enabled. Inspect each desktop/mobile
`extra.ai_recovery` section in its saved website menu JSON for
`used`, `provider`, `reason`, `improved` and `error`. An enabled
option does not mean Codex was invoked when navigation was already healthy.
