import json
from pathlib import Path

import pytest

from src.audit import lighthouse_runner
from src.security.network_policy import UnsafeURLError


def test_lighthouse_version_is_exact_pin_and_lab_parser_does_not_claim_field_data():
    assert lighthouse_runner.lighthouse_version() == "13.4.1"
    metrics = lighthouse_runner.lighthouse_lab_metrics({"categories": {"performance": {"score": 0.83}}, "audits": {"largest-contentful-paint": {"numericValue": 1200}, "cumulative-layout-shift": {"numericValue": 0.02}}})
    assert metrics["dataKind"] == "lab" and metrics["lighthouseLabPerformanceScore"] == 83.0
    assert metrics["labLcpMs"] == 1200.0 and metrics["labCls"] == 0.02


def test_lighthouse_rejects_unsafe_url_before_process(monkeypatch, tmp_path):
    monkeypatch.setattr(lighthouse_runner, "validate_public_url", lambda _: (_ for _ in ()).throw(UnsafeURLError("private address")))
    result = lighthouse_runner.run_lighthouse(url="http://127.0.0.1/", page_id="p", artifacts_dir=tmp_path)
    assert result["measurement"] == "collection_failed" and result["status"] == "failed"


def test_lighthouse_persists_raw_artifact_atomically(monkeypatch, tmp_path):
    class Checked: url = "https://example.test/"
    class Process:
        returncode = 0
        def communicate(self, timeout):
            Path(next(item.split("=", 1)[1] for item in command if item.startswith("--output-path="))).write_text(json.dumps({"categories": {"performance": {"score": 0.5}}, "audits": {}}), encoding="utf-8")
            return "", ""
    command = []
    monkeypatch.setattr(lighthouse_runner, "validate_public_url", lambda _: Checked())
    monkeypatch.setattr(lighthouse_runner, "lighthouse_version", lambda: "13.4.1")
    monkeypatch.setattr(lighthouse_runner, "LIGHTHOUSE_CLI", tmp_path / "cli.js")
    lighthouse_runner.LIGHTHOUSE_CLI.write_text("", encoding="utf-8")
    def popen(args, **kwargs):
        command.extend(args); return Process()
    monkeypatch.setattr(lighthouse_runner.subprocess, "Popen", popen)
    result = lighthouse_runner.run_lighthouse(url="https://example.test/", page_id="page", artifacts_dir=tmp_path)
    assert result["status"] == "completed"
    assert json.loads((tmp_path / "page.json").read_text(encoding="utf-8"))["categories"]["performance"]["score"] == 0.5


def _fake_run(monkeypatch, tmp_path, *, returncode, write_report, stdout=""):
    """Run run_lighthouse against a fake CLI process; returns (result, popen kwargs)."""
    class Checked: url = "https://example.test/"
    seen = {}
    class Process:
        def __init__(self): self.returncode = returncode
        def communicate(self, timeout=None):
            if write_report:
                Path(next(item.split("=", 1)[1] for item in seen["args"] if item.startswith("--output-path="))).write_text(json.dumps({"categories": {"performance": {"score": 0.9}}, "audits": {}}), encoding="utf-8")
            return stdout, ""
    monkeypatch.setattr(lighthouse_runner, "validate_public_url", lambda _: Checked())
    monkeypatch.setattr(lighthouse_runner, "lighthouse_version", lambda: "13.4.1")
    monkeypatch.setattr(lighthouse_runner, "LIGHTHOUSE_CLI", tmp_path / "cli.js")
    lighthouse_runner.LIGHTHOUSE_CLI.write_text("", encoding="utf-8")
    def popen(args, **kwargs):
        seen["args"], seen["kwargs"] = list(args), {**kwargs, "_args": list(args)}
        return Process()
    monkeypatch.setattr(lighthouse_runner.subprocess, "Popen", popen)
    artifacts = tmp_path / "artifacts"
    return lighthouse_runner.run_lighthouse(url="https://example.test/", page_id="page", artifacts_dir=artifacts), seen["kwargs"]


def test_report_written_before_windows_cleanup_error_is_accepted(monkeypatch, tmp_path):
    result, _ = _fake_run(monkeypatch, tmp_path, returncode=1, write_report=True,
                          stdout="Runtime error encountered: EPERM, Permission denied: C:\Temp\lighthouse.123")
    assert result["status"] == "completed" and result["measurement"] == "measured"


def test_nonzero_exit_without_report_still_fails(monkeypatch, tmp_path):
    result, _ = _fake_run(monkeypatch, tmp_path, returncode=1, write_report=False, stdout="No Chrome installations found.")
    assert result["status"] == "failed" and "No Chrome installations found" in result["error"]


def _fake_chromium(root: Path) -> Path:
    executable = root / "chromium-1112" / ("chrome-win/chrome.exe" if lighthouse_runner.os.name == "nt" else "chrome-linux/chrome")
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    return executable


def test_lighthouse_uses_playwright_chromium_when_chrome_path_unset(monkeypatch, tmp_path):
    executable = _fake_chromium(tmp_path / "browsers")
    monkeypatch.delenv("CHROME_PATH", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "browsers"))
    _, kwargs = _fake_run(monkeypatch, tmp_path, returncode=0, write_report=True)
    assert kwargs["env"]["CHROME_PATH"] == str(executable)


def test_lighthouse_respects_configured_chrome_path(monkeypatch, tmp_path):
    _fake_chromium(tmp_path / "browsers")
    monkeypatch.setenv("CHROME_PATH", "D:/chrome/chrome.exe")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "browsers"))
    _, kwargs = _fake_run(monkeypatch, tmp_path, returncode=0, write_report=True)
    assert kwargs["env"]["CHROME_PATH"] == "D:/chrome/chrome.exe"


def test_report_with_runtime_error_is_a_failure(monkeypatch, tmp_path):
    class Checked: url = "https://example.test/"
    seen = {}
    class Process:
        returncode = 1
        def communicate(self, timeout=None):
            Path(next(item.split("=", 1)[1] for item in seen["args"] if item.startswith("--output-path="))).write_text(json.dumps({"runtimeError": {"code": "FAILED_DOCUMENT_REQUEST", "message": "Lighthouse was unable to reliably load the page."}, "categories": {"performance": {"score": None}}, "audits": {}}), encoding="utf-8")
            return "", ""
    monkeypatch.setattr(lighthouse_runner, "validate_public_url", lambda _: Checked())
    monkeypatch.setattr(lighthouse_runner, "lighthouse_version", lambda: "13.4.1")
    monkeypatch.setattr(lighthouse_runner, "LIGHTHOUSE_CLI", tmp_path / "cli.js")
    lighthouse_runner.LIGHTHOUSE_CLI.write_text("", encoding="utf-8")
    monkeypatch.setattr(lighthouse_runner.subprocess, "Popen", lambda args, **kwargs: seen.update(args=list(args)) or Process())
    result = lighthouse_runner.run_lighthouse(url="https://example.test/", page_id="page", artifacts_dir=tmp_path / "a")
    assert result["status"] == "failed" and "unable to reliably load" in result["error"]


def test_desktop_run_uses_the_desktop_preset(monkeypatch, tmp_path):
    # A bare --form-factor=desktop keeps mobile screen emulation, which Lighthouse rejects.
    _, kwargs = _fake_run(monkeypatch, tmp_path, returncode=0, write_report=True)
    args = kwargs["_args"]
    assert "--preset=desktop" in args and "--form-factor=desktop" not in args
