from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_source_has_no_runtime_library_cdn_dependencies():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"https://(?:unpkg\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|esm\.sh)/(?:react|react-dom|gsap)", html)
    source_shell = (ROOT / "src" / "ui" / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'src="/main.jsx"' in source_shell


def test_vite_build_targets_the_python_static_directory():
    config = (ROOT / "vite.config.mjs").read_text(encoding="utf-8")
    assert 'outDir: resolve("src/ui/static/app")' in config
    assert 'base: "/static/app/"' in config


def test_frontend_api_client_centralizes_auth_and_review_error_metadata():
    client = (ROOT / "src" / "ui" / "frontend" / "api" / "client.js").read_text(encoding="utf-8")
    assert 'result.set("Authorization", `Bearer ${token}`)' in client
    assert 'response.headers.get("x-request-id")' in client
    assert "status: response.status" in client
    assert "createApiClient" in client


def test_frontend_uses_session_bearer_and_has_no_public_tunnel_default():
    html = (ROOT / "src" / "ui" / "static" / "index.html").read_text(encoding="utf-8")
    config = (ROOT / "src" / "ui" / "static" / "config.js").read_text(encoding="utf-8")
    client = (ROOT / "src" / "ui" / "frontend" / "api" / "client.js").read_text(encoding="utf-8")
    assert 'result.set("Authorization", `Bearer ${token}`)' in client
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
