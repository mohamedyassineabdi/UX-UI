from __future__ import annotations

from pathlib import Path

import pytest

from src.gtm_audit.vercel_static_deploy import publish_selected_report


def make_report(path: Path, marker: str):
    path.mkdir(parents=True)
    (path / "index.html").write_text(f"<!doctype html><p>{marker}</p>", encoding="utf-8")
    (path / "asset.txt").write_text(marker, encoding="utf-8")


def test_selected_publication_contains_no_other_audit_and_cleans_stage(tmp_path):
    audit_a = tmp_path / "source" / "a"
    audit_b = tmp_path / "source" / "b"
    make_report(audit_a, "AUDIT_A")
    make_report(audit_b, "AUDIT_B")
    staging_parent = tmp_path / "staging"
    staging_parent.mkdir()

    observed = {}

    def deployer(stage, **kwargs):
        observed["stage"] = Path(stage)
        observed["contents"] = [p.read_text(encoding="utf-8") for p in Path(stage).rglob("*") if p.is_file()]
        observed["public_path"] = kwargs["public_path"]
        return "https://example.vercel.app/" + kwargs["public_path"] + "/"

    url = publish_selected_report(audit_a, deployer=deployer, staging_parent=staging_parent)
    assert "AUDIT_A" in " ".join(observed["contents"])
    assert "AUDIT_B" not in " ".join(observed["contents"])
    assert "/audits/" in url
    assert not observed["stage"].exists()
    assert list(staging_parent.iterdir()) == []


def test_failed_deployment_preserves_source_and_cleans_stage(tmp_path):
    report = tmp_path / "report"
    make_report(report, "ORIGINAL")
    staging_parent = tmp_path / "staging"
    staging_parent.mkdir()
    before = (report / "index.html").read_bytes()

    def fail(_stage, **_kwargs):
        raise RuntimeError("mock failure")

    with pytest.raises(RuntimeError):
        publish_selected_report(report, deployer=fail, staging_parent=staging_parent)
    assert (report / "index.html").read_bytes() == before
    assert list(staging_parent.iterdir()) == []


def test_outside_asset_reference_and_symlink_are_rejected(tmp_path, monkeypatch):
    report = tmp_path / "report"
    make_report(report, "ORIGINAL")
    (report / "index.html").write_text('<!doctype html><img src="../secret.txt">', encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError):
        publish_selected_report(report, deployer=lambda *_args, **_kwargs: "unused")

    (report / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (report / "link.txt").write_text("simulated link", encoding="utf-8")
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "link.txt" or original_is_symlink(self))
    with pytest.raises(ValueError):
        publish_selected_report(report, deployer=lambda *_args, **_kwargs: "unused")
