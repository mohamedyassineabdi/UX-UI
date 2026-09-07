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
