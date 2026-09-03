from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JOB_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def validate_job_id(job_id: str) -> str:
    value = str(job_id or "").strip()
    if not JOB_ID_RE.fullmatch(value):
        raise ValueError("Invalid audit job identifier.")
    return value


def atomic_write_bytes(destination: Path, content: bytes) -> None:
    """Atomically replace a file with a same-directory temporary file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(destination: Path, content: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(destination, content.encode(encoding))


def atomic_write_json(destination: Path, payload: Any) -> None:
    atomic_write_text(destination, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


@dataclass(frozen=True)
class AuditWorkspace:
    """Deterministic, containment-checked generated-artifact paths for one audit."""

    job_id: str
    audits_dir: Path

    def __post_init__(self) -> None:
        job_id = validate_job_id(self.job_id)
        audits_dir = Path(self.audits_dir).resolve()
        root = audits_dir / job_id
        if root.parent != audits_dir:
            raise ValueError("Audit workspace escapes its configured root.")
        object.__setattr__(self, "job_id", job_id)
        object.__setattr__(self, "audits_dir", audits_dir)

    @classmethod
    def for_repository(cls, job_id: str, repository_root: Path | None = None) -> "AuditWorkspace":
        root = repository_root or Path(__file__).resolve().parents[2]
        return cls(job_id=job_id, audits_dir=Path(root) / "shared" / "audits")

    @property
    def root(self) -> Path:
        return self.audits_dir / self.job_id

    @property
    def manifest(self) -> Path:
        return self.root / "job.json"

    @property
    def input_dir(self) -> Path:
        return self.root / "input"

    @property
    def website_menu(self) -> Path:
        return self.input_dir / "website_menu.json"

    @property
    def extraction_dir(self) -> Path:
        return self.root / "extraction"

    @property
    def audit_results(self) -> Path:
        return self.extraction_dir / "audit_results.json"

    @property
    def html_extraction(self) -> Path:
        return self.extraction_dir / "html_extraction.json"

    @property
    def html_cleaned(self) -> Path:
        return self.extraction_dir / "html_cleaned.json"

    @property
    def rendered_ui(self) -> Path:
        return self.extraction_dir / "rendered_ui_extraction.json"

    @property
    def checks_dir(self) -> Path:
        return self.root / "checks"

    @property
    def checks(self) -> Path:
        return self.checks_dir / "sheet_checks.json"

    @property
    def screenshots(self) -> Path:
        return self.root / "screenshots"

    @property
    def page_screenshots(self) -> Path:
        return self.screenshots / "pages"

    @property
    def interaction_screenshots(self) -> Path:
        return self.screenshots / "interactions"

    @property
    def audit_dir(self) -> Path:
        return self.root / "audit"

    @property
    def gtm_audit(self) -> Path:
        return self.audit_dir / "gtm_audit.json"

    @property
    def workbook_dir(self) -> Path:
        return self.root / "workbook"

    @property
    def workbook(self) -> Path:
        return self.workbook_dir / "UX-Audit-Workbook-final.xlsx"

    @property
    def report(self) -> Path:
        return self.root / "report"

    @property
    def publication(self) -> Path:
        return self.root / "publication"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def coverage_dir(self) -> Path:
        return self.root / "coverage"

    @property
    def coverage_manifest(self) -> Path:
        return self.coverage_dir / "manifest.json"

    @property
    def run_config(self) -> Path:
        return self.input_dir / "run_config.json"

    def prepare(self, *, mode: str) -> None:
        if self.root.exists() and self.root.is_symlink():
            raise ValueError("Audit workspace may not be a symlink.")
        for directory in (
            self.input_dir,
            self.extraction_dir,
            self.checks_dir,
            self.page_screenshots,
            self.interaction_screenshots,
            self.audit_dir,
            self.workbook_dir,
            self.report,
            self.publication,
            self.logs,
            self.coverage_dir,
        ):
            if directory.exists() and directory.is_symlink():
                raise ValueError("Audit workspace directory may not be a symlink.")
            directory.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            self.manifest,
            {
                "schemaVersion": 1,
                "jobId": self.job_id,
                "auditType": "website",
                "mode": mode,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "paths": {
                    "websiteMenu": str(self.website_menu.relative_to(self.root)),
                    "auditResults": str(self.audit_results.relative_to(self.root)),
                    "htmlExtraction": str(self.html_extraction.relative_to(self.root)),
                    "htmlCleaned": str(self.html_cleaned.relative_to(self.root)),
                    "renderedUi": str(self.rendered_ui.relative_to(self.root)),
                    "checks": str(self.checks.relative_to(self.root)),
                    "gtmAudit": str(self.gtm_audit.relative_to(self.root)),
                    "report": str(self.report.relative_to(self.root)),
                    "publication": str(self.publication.relative_to(self.root)),
                    "coverageManifest": str(self.coverage_manifest.relative_to(self.root)),
                },
            },
        )
