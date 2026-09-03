from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from src.audit.workspace import AuditWorkspace

from .store import JobStore


class AuditStorageManager:
    """Retention and quota cleanup limited to validated Phase 1A workspaces."""

    def __init__(self, store: JobStore, audits_dir: Path, *, retention_days: int | None = None, max_bytes: int | None = None):
        self.store = store
        self.audits_dir = Path(audits_dir)
        self.retention_days = retention_days if retention_days is not None else _nonnegative_env("UX_AUDIT_RETENTION_DAYS", 30)
        self.max_bytes = max_bytes if max_bytes is not None else _nonnegative_env("UX_AUDIT_STORAGE_MAX_BYTES", 5 * 1024 * 1024 * 1024)

    def usage_bytes(self) -> int:
        if not self.audits_dir.exists():
            return 0
        return sum(path.stat().st_size for path in self.audits_dir.rglob("*") if path.is_file() and not path.is_symlink())

    def cleanup(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        removed: list[str] = []
        if self.retention_days:
            cutoff = now - self.retention_days * 86400
            for job in self.store.terminal_jobs_before(cutoff):
                self._delete_workspace(str(job["id"])); removed.append(str(job["id"]))
        if self.max_bytes:
            for job in self.store.terminal_jobs_before(None):
                if self.usage_bytes() <= self.max_bytes:
                    break
                job_id = str(job["id"])
                if job_id not in removed:
                    self._delete_workspace(job_id); removed.append(job_id)
        return removed

    def can_accept(self) -> bool:
        self.cleanup()
        return not self.max_bytes or self.usage_bytes() < self.max_bytes

    def _delete_workspace(self, job_id: str) -> None:
        workspace = AuditWorkspace(job_id, self.audits_dir)
        root = workspace.root
        if root.exists():
            resolved_root = root.resolve()
            resolved_root.relative_to(self.audits_dir.resolve())
            if root.is_symlink():
                raise ValueError("Refusing to remove symlinked audit workspace.")
            shutil.rmtree(root)
        self.store.tombstone(job_id)


def _nonnegative_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a non-negative integer.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be a non-negative integer.")
    return value
