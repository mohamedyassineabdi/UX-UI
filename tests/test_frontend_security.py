from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_external_launcher_scripts_are_exact_and_have_integrity():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    tags = re.findall(r"<script\b[^>]*\bsrc=\"https://[^\"]+\"[^>]*>", html)
    assert tags
    for tag in tags:
        assert "integrity=\"sha384-" in tag
        assert "crossorigin=\"anonymous\"" in tag
        assert re.search(r"@[0-9]+\.[0-9]+\.[0-9]+/", tag)


def test_frontend_uses_session_bearer_and_has_no_public_tunnel_default():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    config = (ROOT / "src" / "ui" / "static" / "config.js").read_text(encoding="utf-8")
    assert 'headers.set("Authorization", `Bearer ${portalToken}`)' in html
    assert "trycloudflare.com" not in config
    assert "ngrok" not in config.lower()


def test_report_generators_submit_no_html_payload():
    combined = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in ("src/gtm_audit/generate_gtm_report.py", "figma_audit/reports.py")
    )
    assert "/api/reports/deploy" not in combined
    assert "cleanCloneForDeployment" not in combined
    assert '"Authorization": `Bearer ${token}`' in combined
