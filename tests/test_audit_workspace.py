from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.audit import workspace as workspace_module
from src.audit.workspace import AuditWorkspace, atomic_write_json, atomic_write_text


def test_workspaces_are_deterministic_and_cannot_mix_artifacts(tmp_path):
    audit_a = AuditWorkspace("job-a", tmp_path / "audits")
    audit_b = AuditWorkspace("job-b", tmp_path / "audits")
    audit_a.prepare(mode="gtm")
    audit_b.prepare(mode="gtm")

    assert audit_a.root != audit_b.root
    assert audit_a.website_menu != audit_b.website_menu
    assert audit_a.audit_results != audit_b.audit_results
    assert audit_a.checks != audit_b.checks
    assert audit_a.report != audit_b.report
    assert audit_a.screenshots != audit_b.screenshots
    assert audit_a.publication != audit_b.publication

    atomic_write_json(audit_a.audit_results, {"job": "a"})
    atomic_write_json(audit_b.audit_results, {"job": "b"})
    os.utime(audit_b.audit_results, (9_999_999_999, 9_999_999_999))

    assert json.loads(audit_a.audit_results.read_text(encoding="utf-8"))["job"] == "a"
    assert json.loads(audit_b.audit_results.read_text(encoding="utf-8"))["job"] == "b"


@pytest.mark.parametrize("job_id", ["", "../outside", "..\\outside", "/absolute", "C:\\outside", "job%2fother", "space id"])
def test_workspace_rejects_path_traversal_and_noncanonical_ids(tmp_path, job_id):
    with pytest.raises(ValueError):
        AuditWorkspace(job_id, tmp_path / "audits")


def test_parallel_workspace_writes_are_isolated(tmp_path):
    audits_dir = tmp_path / "audits"

    def write_run(job_id: str) -> AuditWorkspace:
        workspace = AuditWorkspace(job_id, audits_dir)
        workspace.prepare(mode="gtm")
        atomic_write_json(workspace.website_menu, {"job": job_id})
        atomic_write_json(workspace.audit_results, {"job": job_id, "result": "complete"})
        atomic_write_json(workspace.checks, {"job": job_id, "checks": []})
        atomic_write_text(workspace.report / "index.html", f"report-{job_id}")
        return workspace

    with ThreadPoolExecutor(max_workers=2) as executor:
        audit_a, audit_b = list(executor.map(write_run, ("parallel-a", "parallel-b")))

    assert audit_a.report.joinpath("index.html").read_text(encoding="utf-8") == "report-parallel-a"
    assert audit_b.report.joinpath("index.html").read_text(encoding="utf-8") == "report-parallel-b"
    assert "parallel-b" not in audit_a.audit_results.read_text(encoding="utf-8")
    assert "parallel-a" not in audit_b.audit_results.read_text(encoding="utf-8")


def test_atomic_writes_use_unique_same_directory_temporary_files(tmp_path, monkeypatch):
    destination = tmp_path / "state.json"
    observed: list[Path] = []
    real_replace = workspace_module.os.replace

    def record_replace(source, target):
        source_path, target_path = Path(source), Path(target)
        assert source_path.parent == target_path.parent
        observed.append(source_path)
        return real_replace(source, target)

    monkeypatch.setattr(workspace_module.os, "replace", record_replace)
    atomic_write_json(destination, {"version": 1})
    atomic_write_json(destination, {"version": 2})

    assert len(observed) == 2
    assert observed[0].name != observed[1].name
    assert json.loads(destination.read_text(encoding="utf-8")) == {"version": 2}


def test_failed_atomic_write_preserves_existing_destination(tmp_path, monkeypatch):
    destination = tmp_path / "state.json"
    atomic_write_text(destination, "old")
    monkeypatch.setattr(workspace_module.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("replace failed")))

    with pytest.raises(OSError, match="replace failed"):
        atomic_write_text(destination, "new")

    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob(".state.json.*.tmp"))
