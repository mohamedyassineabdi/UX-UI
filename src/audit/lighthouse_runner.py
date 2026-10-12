"""Pinned Lighthouse lab runner with the same public-URL boundary as audits."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

from src.audit.workspace import atomic_write_json
from src.security.network_policy import UnsafeURLError, validate_public_url


ROOT = Path(__file__).resolve().parents[2]
LIGHTHOUSE_CLI = ROOT / "node_modules" / "lighthouse" / "cli" / "index.js"
LIGHTHOUSE_PACKAGE = ROOT / "node_modules" / "lighthouse" / "package.json"
LAB_CONFIGURATION = {
    "onlyCategories": ["performance"], "formFactor": "desktop",
    "throttlingMethod": "simulate", "dataKind": "lab",
}


def lighthouse_version() -> str | None:
    try:
        return str(json.loads(LIGHTHOUSE_PACKAGE.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def lighthouse_lab_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    categories = raw.get("categories") if isinstance(raw.get("categories"), dict) else {}
    audits = raw.get("audits") if isinstance(raw.get("audits"), dict) else {}
    def numeric(audit_id: str) -> float | None:
        value = (audits.get(audit_id) or {}).get("numericValue") if isinstance(audits.get(audit_id), dict) else None
        return float(value) if isinstance(value, (int, float)) else None
    performance = (categories.get("performance") or {}).get("score") if isinstance(categories.get("performance"), dict) else None
    return {
        "dataKind": "lab", "label": "Lighthouse lab performance",
        "lighthouseLabPerformanceScore": round(float(performance) * 100, 1) if isinstance(performance, (int, float)) else None,
        "labLcpMs": numeric("largest-contentful-paint"), "labCls": numeric("cumulative-layout-shift"),
        "labFcpMs": numeric("first-contentful-paint"), "labTbtMs": numeric("total-blocking-time"),
        "labSpeedIndexMs": numeric("speed-index"),
    }


_PLAYWRIGHT_CHROMIUM = ("chrome-win/chrome.exe", "chrome-linux/chrome", "chrome-mac/Chromium.app/Contents/MacOS/Chromium")


def _playwright_chromium() -> str | None:
    """Playwright's newest installed Chromium, found on disk.

    Lighthouse's launcher only finds a system Chrome. The audit already
    depends on Playwright's Chromium, so reuse it. A directory scan (not the
    Playwright API) keeps this safe inside the pipeline's asyncio loop.
    """
    configured = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured:
        root = Path(configured)
    elif os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "ms-playwright"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        root = Path.home() / ".cache" / "ms-playwright"
    def revision(folder: Path) -> int:
        suffix = folder.name.rsplit("-", 1)[-1]
        return int(suffix) if suffix.isdigit() else -1
    for folder in sorted(root.glob("chromium-*"), key=revision, reverse=True):
        for relative in _PLAYWRIGHT_CHROMIUM:
            if (folder / relative).is_file():
                return str(folder / relative)
    return None


def _lighthouse_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("CHROME_PATH", "").strip():
        chromium = _playwright_chromium()
        if chromium:
            env["CHROME_PATH"] = chromium
    return env


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        process.kill()


def run_lighthouse(*, url: str, page_id: str, artifacts_dir: Path, timeout_seconds: int = 120) -> dict[str, Any]:
    """Run the installed CLI only after SSRF validation; failure never implies a score."""
    version = lighthouse_version()
    if not version or not LIGHTHOUSE_CLI.is_file():
        return {"measurement": "not_measured", "status": "unavailable", "pageId": page_id,
                "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "configuration": LAB_CONFIGURATION}
    try:
        checked = validate_public_url(url)
    except UnsafeURLError as exc:
        return {"measurement": "collection_failed", "status": "failed", "pageId": page_id,
                "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "error": str(exc)[:300], "configuration": LAB_CONFIGURATION}
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    destination = artifacts_dir / f"{page_id}.json"
    started = perf_counter()
    with tempfile.TemporaryDirectory(dir=artifacts_dir) as temporary:
        output_path = Path(temporary) / "lighthouse.json"
        command = [sys.executable.replace("python.exe", "node.exe"), str(LIGHTHOUSE_CLI), checked.url,
                   "--quiet", "--output=json", f"--output-path={output_path}", "--only-categories=performance",
                   "--preset=desktop", "--throttling-method=simulate"]
        # sys.executable is a Python interpreter; explicitly use Node when its
        # sibling is not present (as is normal for a uv environment).
        command[0] = os.environ.get("NODE_BINARY", "node")
        creation = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)} if os.name == "nt" else {}
        process = subprocess.Popen(command, cwd=ROOT, env=_lighthouse_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **creation)
        try:
            stdout, _ = process.communicate(timeout=max(1, timeout_seconds))
        except subprocess.TimeoutExpired:
            _terminate_tree(process)
            process.communicate()
            return {"measurement": "collection_failed", "status": "failed", "pageId": page_id, "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "error": "Lighthouse lab execution timed out.", "configuration": LAB_CONFIGURATION, "durationMs": round((perf_counter() - started) * 1000)}
        # On Windows the CLI can exit non-zero after writing the report, when it
        # fails to delete its Chrome profile (EPERM). A written report counts.
        if not output_path.is_file():
            return {"measurement": "collection_failed", "status": "failed", "pageId": page_id, "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "error": (stdout or "Lighthouse did not produce a report.")[-300:], "configuration": LAB_CONFIGURATION, "durationMs": round((perf_counter() - started) * 1000)}
        try:
            raw = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"measurement": "collection_failed", "status": "failed", "pageId": page_id, "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "error": f"Invalid Lighthouse JSON: {exc}"[:300], "configuration": LAB_CONFIGURATION, "durationMs": round((perf_counter() - started) * 1000)}
        runtime_error = raw.get("runtimeError") if isinstance(raw, dict) else None
        if isinstance(runtime_error, dict) and runtime_error:
            message = f"{runtime_error.get('code', 'RUNTIME_ERROR')}: {runtime_error.get('message', '')}"
            return {"measurement": "collection_failed", "status": "failed", "pageId": page_id, "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "error": message[:300], "configuration": LAB_CONFIGURATION, "durationMs": round((perf_counter() - started) * 1000)}
    atomic_write_json(destination, raw)
    return {"measurement": "measured", "status": "completed", "pageId": page_id, "auditUrl": checked.url,
            "tool": "lighthouse", "toolVersion": version, "dataKind": "lab", "configuration": LAB_CONFIGURATION,
            "artifactPath": str(destination), "labMetrics": lighthouse_lab_metrics(raw), "durationMs": round((perf_counter() - started) * 1000)}
