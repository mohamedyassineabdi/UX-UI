from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.audit.workspace import AuditWorkspace, atomic_write_json, atomic_write_text


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("website_pipeline_under_test", ROOT_DIR / "scripts" / "run_pipeline.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pipeline_args(job_id: str) -> argparse.Namespace:
    return argparse.Namespace(
        url="https://example.test/",
        job_id=job_id,
        mode="gtm",
        workbook_template="",
        skip_workbook=False,
        skip_vision=True,
        deploy_vercel=False,
        vercel_preview=False,
        vercel_prod=False,
    )


def option(command, flag: str) -> Path:
    values = [str(value) for value in command]
    return Path(values[values.index(flag) + 1])


def test_simulated_parallel_pipelines_use_only_their_own_explicit_artifacts(tmp_path, monkeypatch):
    pipeline = load_pipeline_module()
    monkeypatch.setattr(pipeline, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "NAVIGATOR_DIR", tmp_path / "navigator")
    consumed_results: dict[str, str] = {}

    def fake_run(command, **_kwargs):
        values = [str(value) for value in command]
        if values[1].endswith("crawler.py"):
            atomic_write_json(option(values, "--json-out"), {"homepage": "https://example.test/", "navigation": []})
        elif values[1:3] == ["-m", "src.main"]:
            workspace = AuditWorkspace(option(values, "--job-id").name, tmp_path / "shared" / "audits")
            atomic_write_json(workspace.audit_results, {"job": workspace.job_id})
            atomic_write_json(workspace.html_cleaned, {"pages": []})
            atomic_write_json(workspace.rendered_ui, {"pages": []})
        elif values[1:3] == ["-m", "src.audit.checks.run_sheet_checks"]:
            atomic_write_json(option(values, "--output"), {"sheets": {}})
        elif values[1:3] == ["-m", "src.gtm_audit.generate_gtm_audit"]:
            results = option(values, "--results")
            consumed_results[results.parent.parent.name] = results.read_text(encoding="utf-8")
            atomic_write_json(option(values, "--output"), {"artifacts": {}})
        elif values[1:3] == ["-m", "src.gtm_audit.generate_gtm_report"]:
            output_dir = option(values, "--output-dir")
            atomic_write_text(output_dir / "index.html", "report")
        else:
            raise AssertionError(f"Unexpected pipeline command: {values}")

    monkeypatch.setattr(pipeline, "run_command", fake_run)
    monkeypatch.setattr(pipeline, "run_command_capture", lambda *_args, **_kwargs: "")

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(pipeline.run_pipeline, (pipeline_args("pipeline-a"), pipeline_args("pipeline-b"))))

    workspace_a = AuditWorkspace("pipeline-a", tmp_path / "shared" / "audits")
    workspace_b = AuditWorkspace("pipeline-b", tmp_path / "shared" / "audits")
    os.utime(workspace_b.audit_results, (9_999_999_999, 9_999_999_999))

    assert "pipeline-a" in consumed_results["pipeline-a"]
    assert "pipeline-b" in consumed_results["pipeline-b"]
    assert workspace_a.report.joinpath("index.html").exists()
    assert workspace_b.report.joinpath("index.html").exists()
    assert workspace_a.audit_results != workspace_b.audit_results
