from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .models import JobStatus, TERMINAL_STATUSES, can_transition


class JobStore:
    """SQLite-backed authoritative audit-job state for a single instance.

    SQLite's BEGIN IMMEDIATE transaction serializes writers, making a claim atomic on
    one host. Distributed mode is deliberately rejected by the server until a shared
    backend is configured; a local SQLite file must never be treated as ECS locking.
    """

    SCHEMA_VERSION = 1

    def __init__(self, database_path: Path | str):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._initialize()

    @classmethod
    def from_environment(cls, root: Path) -> "JobStore":
        raw = os.getenv("UX_JOB_DATABASE_URL", "").strip()
        if raw and not raw.startswith("sqlite:///"):
            raise RuntimeError("Only sqlite:/// job database URLs are supported by this deployment. Configure a shared PostgreSQL job store before using distributed mode.")
        path = Path(raw.removeprefix("sqlite:///")) if raw else root / "shared" / "state" / "jobs.sqlite3"
        return cls(path)

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection = connection
        return connection

    def close(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def _initialize(self) -> None:
        connection = self._connection()
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at REAL NOT NULL)")
        applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        if self.SCHEMA_VERSION not in applied:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY,
                  owner_id TEXT NOT NULL,
                  owner_role TEXT NOT NULL DEFAULT '',
                  audit_type TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  status TEXT NOT NULL,
                  stage TEXT NOT NULL,
                  progress INTEGER NOT NULL DEFAULT 0,
                  result_url TEXT NOT NULL DEFAULT '',
                  error TEXT NOT NULL DEFAULT '',
                  cancel_requested INTEGER NOT NULL DEFAULT 0,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  started_at REAL,
                  worker_id TEXT,
                  lease_expires_at REAL,
                  heartbeat_at REAL,
                  attempt_count INTEGER NOT NULL DEFAULT 0,
                  last_failure_class TEXT NOT NULL DEFAULT '',
                  last_failure_at REAL,
                  publication_status TEXT NOT NULL DEFAULT 'not_requested',
                  publication_url TEXT NOT NULL DEFAULT '',
                  artifacts_deleted INTEGER NOT NULL DEFAULT 0,
                  expired_at REAL
                );
                CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs(status, created_at);
                CREATE INDEX IF NOT EXISTS jobs_lease_idx ON jobs(status, lease_expires_at);
                CREATE INDEX IF NOT EXISTS jobs_owner_idx ON jobs(owner_id, created_at);
                CREATE TABLE IF NOT EXISTS job_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                  created_at REAL NOT NULL,
                  level TEXT NOT NULL,
                  event TEXT NOT NULL,
                  message TEXT NOT NULL,
                  request_id TEXT NOT NULL DEFAULT '',
                  worker_id TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS job_events_job_idx ON job_events(job_id, id);
                """
            )
            connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (self.SCHEMA_VERSION, time.time()))

    @staticmethod
    def _row(row: sqlite3.Row | None, events: list[str] | None = None) -> dict[str, Any] | None:
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        job = dict(payload)
        job.update({
            "id": row["id"], "ownerId": row["owner_id"], "ownerRole": row["owner_role"], "type": row["audit_type"],
            "status": row["status"], "stage": row["stage"], "progress": row["progress"], "resultUrl": row["result_url"],
            "error": row["error"], "cancelRequested": bool(row["cancel_requested"]), "createdAt": row["created_at"],
            "updatedAt": row["updated_at"], "startedAt": row["started_at"], "workerId": row["worker_id"] or "",
            "leaseExpiresAt": row["lease_expires_at"], "heartbeatAt": row["heartbeat_at"], "attemptCount": row["attempt_count"],
            "lastFailureClass": row["last_failure_class"], "lastFailureAt": row["last_failure_at"],
            "publicationStatus": row["publication_status"], "publicationUrl": row["publication_url"],
            "artifactsDeleted": bool(row["artifacts_deleted"]), "expiredAt": row["expired_at"],
            "logs": events or [],
        })
        return job

    def _events(self, job_id: str, limit: int = 200) -> list[str]:
        rows = self._connection().execute("SELECT message FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT ?", (job_id, limit)).fetchall()
        return [str(row[0]) for row in reversed(rows)]

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self._connection().execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row(row, self._events(job_id) if row else None)

    def get_owned(self, job_id: str, owner_id: str) -> dict[str, Any] | None:
        row = self._connection().execute("SELECT * FROM jobs WHERE id=? AND owner_id=?", (job_id, owner_id)).fetchone()
        return self._row(row, self._events(job_id) if row else None)

    def owns(self, job_id: str, owner_id: str) -> bool:
        return self._connection().execute("SELECT 1 FROM jobs WHERE id=? AND owner_id=?", (job_id, owner_id)).fetchone() is not None

    def create(self, job: dict[str, Any], *, owner_id: str, owner_role: str = "", request_id: str = "") -> dict[str, Any]:
        job_id = str(job.get("id") or uuid.uuid4().hex[:12])
        if not job_id.isalnum() or len(job_id) > 64:
            raise ValueError("Invalid audit identifier.")
        now = time.time()
        payload = dict(job)
        for key in ("id", "ownerId", "ownerRole", "ownerEmail", "status", "stage", "progress", "logs", "resultUrl", "error", "cancelRequested", "createdAt", "updatedAt"):
            payload.pop(key, None)
        audit_type = str(job.get("type") or "website")
        connection = self._connection()
        connection.execute(
            "INSERT INTO jobs(id,owner_id,owner_role,audit_type,payload_json,status,stage,progress,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (job_id, owner_id, owner_role, audit_type, json.dumps(payload, ensure_ascii=False, sort_keys=True), JobStatus.QUEUED, "Queued", 0, now, now),
        )
        self.event(job_id, "info", "queued", "Audit job queued.", request_id=request_id)
        return self.get(job_id) or raise_missing(job_id)

    def event(self, job_id: str, level: str, event: str, message: str, *, request_id: str = "", worker_id: str = "") -> None:
        self._connection().execute("INSERT INTO job_events(job_id,created_at,level,event,message,request_id,worker_id) VALUES (?,?,?,?,?,?,?)", (job_id, time.time(), level, event, message[-4000:], request_id, worker_id))

    def update(self, job_id: str, *, request_id: str = "", event: str = "updated", **updates: Any) -> dict[str, Any] | None:
        current = self.get(job_id)
        if current is None:
            return None
        target_status = str(updates.pop("status", current["status"]))
        if target_status != current["status"] and not can_transition(current["status"], target_status):
            raise ValueError(f"Invalid audit job transition: {current['status']} -> {target_status}.")
        if target_status == JobStatus.FAILED and current["status"] != JobStatus.FAILED:
            updates.setdefault("lastFailureClass", "unknown")
            updates.setdefault("lastFailureAt", time.time())
        columns: dict[str, Any] = {"status": target_status, "updated_at": time.time()}
        mapping = {"stage":"stage", "progress":"progress", "resultUrl":"result_url", "error":"error", "cancelRequested":"cancel_requested", "publicationStatus":"publication_status", "publicationUrl":"publication_url", "lastFailureClass":"last_failure_class", "lastFailureAt":"last_failure_at", "outputDir":None, "previewImagePath":None}
        payload = {key: value for key, value in current.items() if key not in {"id", "ownerId", "ownerRole", "type", "status", "stage", "progress", "resultUrl", "error", "cancelRequested", "createdAt", "updatedAt", "startedAt", "workerId", "leaseExpiresAt", "heartbeatAt", "attemptCount", "lastFailureClass", "lastFailureAt", "publicationStatus", "publicationUrl", "artifactsDeleted", "expiredAt", "logs"}}
        for key, value in updates.items():
            column = mapping.get(key)
            if column:
                columns[column] = int(bool(value)) if key == "cancelRequested" else value
            elif key not in {"logs"}:
                payload[key] = value
        columns["payload_json"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        assignments = ", ".join(f"{name}=?" for name in columns)
        self._connection().execute(f"UPDATE jobs SET {assignments} WHERE id=?", (*columns.values(), job_id))
        self.event(job_id, "info", event, str(updates.get("error") or updates.get("stage") or "Job updated."), request_id=request_id)
        return self.get(job_id)

    def request_cancel(self, job_id: str) -> tuple[dict[str, Any] | None, bool]:
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None, False
            status = str(row["status"])
            now = time.time()
            if status == JobStatus.QUEUED:
                connection.execute("UPDATE jobs SET status=?,cancel_requested=1,stage=?,progress=100,error=?,updated_at=? WHERE id=?", (JobStatus.CANCELLED, "Audit stopped", "Audit stopped by user.", now, job_id))
                changed = True
            elif status == JobStatus.RUNNING:
                connection.execute("UPDATE jobs SET cancel_requested=1,stage=?,updated_at=? WHERE id=?", ("Cancellation requested", now, job_id))
                changed = True
            else:
                changed = False
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        if changed:
            self.event(job_id, "info", "cancel_requested", "Audit cancellation requested.")
        return self.get(job_id), changed

    def claim_next(self, worker_id: str, lease_seconds: float) -> dict[str, Any] | None:
        connection = self._connection()
        now = time.time()
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute("SELECT * FROM jobs WHERE status=? AND cancel_requested=0 ORDER BY created_at,id LIMIT 1", (JobStatus.QUEUED,)).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            job_id = str(row["id"])
            updated = connection.execute("UPDATE jobs SET status=?,worker_id=?,lease_expires_at=?,heartbeat_at=?,started_at=COALESCE(started_at,?),attempt_count=attempt_count+1,updated_at=? WHERE id=? AND status=? AND cancel_requested=0", (JobStatus.RUNNING, worker_id, now + lease_seconds, now, now, now, job_id, JobStatus.QUEUED)).rowcount
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        if not updated:
            return None
        self.event(job_id, "info", "claimed", "Audit job claimed by worker.", worker_id=worker_id)
        return self.get(job_id)

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: float) -> bool:
        now = time.time()
        count = self._connection().execute("UPDATE jobs SET heartbeat_at=?,lease_expires_at=?,updated_at=? WHERE id=? AND status=? AND worker_id=?", (now, now + lease_seconds, now, job_id, JobStatus.RUNNING, worker_id)).rowcount
        return bool(count)

    def finish(self, job_id: str, worker_id: str, status: JobStatus, *, error: str = "", failure_class: str = "") -> dict[str, Any] | None:
        if status not in TERMINAL_STATUSES and status is not JobStatus.INTERRUPTED:
            raise ValueError("Job may only be finished in a terminal or interrupted state.")
        current = self.get(job_id)
        if current is None or current.get("workerId") != worker_id:
            return current
        if current.get("cancelRequested"):
            status, error = JobStatus.CANCELLED, "Audit stopped by user."
        updates: dict[str, Any] = {"status": str(status), "stage": "Audit stopped" if status is JobStatus.CANCELLED else current.get("stage", ""), "progress": 100 if status in TERMINAL_STATUSES else current.get("progress", 0), "error": error}
        if status is JobStatus.FAILED:
            updates.update({"lastFailureClass": failure_class or "unknown", "lastFailureAt": time.time()})
        return self.update(job_id, event="finished", **updates)

    def reap_expired(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            rows = connection.execute("SELECT id FROM jobs WHERE status=? AND lease_expires_at IS NOT NULL AND lease_expires_at<?", (JobStatus.RUNNING, now)).fetchall()
            ids = [str(row[0]) for row in rows]
            if ids:
                connection.executemany("UPDATE jobs SET status=?,stage=?,error=?,worker_id=NULL,lease_expires_at=NULL,updated_at=?,last_failure_class=?,last_failure_at=? WHERE id=? AND status=?", [(JobStatus.INTERRUPTED, "Interrupted after worker lease expired", "Worker lease expired; audit was not retried automatically.", now, "worker_lease_expired", now, job_id, JobStatus.RUNNING) for job_id in ids])
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        for job_id in ids:
            self.event(job_id, "warning", "interrupted", "Worker lease expired; audit was marked interrupted.")
        return ids

    def queued_count(self) -> int:
        return int(self._connection().execute("SELECT COUNT(*) FROM jobs WHERE status=?", (JobStatus.QUEUED,)).fetchone()[0])

    def metrics(self) -> dict[str, Any]:
        row = self._connection().execute("SELECT SUM(status='queued'), SUM(status='running'), MIN(CASE WHEN status='queued' THEN created_at END) FROM jobs WHERE artifacts_deleted=0").fetchone()
        return {"queued": int(row[0] or 0), "running": int(row[1] or 0), "oldestQueuedAt": row[2]}

    def terminal_jobs_before(self, cutoff: float | None) -> list[dict[str, Any]]:
        statuses = tuple(str(status) for status in TERMINAL_STATUSES)
        if cutoff is None:
            rows = self._connection().execute("SELECT * FROM jobs WHERE status IN (?,?,?) AND artifacts_deleted=0 ORDER BY updated_at,id", statuses).fetchall()
        else:
            rows = self._connection().execute("SELECT * FROM jobs WHERE status IN (?,?,?) AND artifacts_deleted=0 AND updated_at<? ORDER BY updated_at,id", statuses + (cutoff,)).fetchall()
        return [self._row(row, []) for row in rows if row]

    def tombstone(self, job_id: str) -> None:
        self._connection().execute("UPDATE jobs SET artifacts_deleted=1,expired_at=?,updated_at=? WHERE id=?", (time.time(), time.time(), job_id))
        self.event(job_id, "info", "artifacts_deleted", "Audit artifacts deleted by retention policy.")


def raise_missing(job_id: str) -> None:
    raise RuntimeError(f"Job {job_id} was not persisted.")
