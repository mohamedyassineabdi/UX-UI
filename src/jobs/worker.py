from __future__ import annotations

import os
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from .models import JobStatus
from .store import JobStore


class AuditWorker:
    """Bounded local worker pool that claims durable jobs before execution."""

    def __init__(self, store: JobStore, execute: Callable[[str], None], *, concurrency: int | None = None, lease_seconds: float | None = None, poll_seconds: float = 0.25):
        self.store = store
        self.execute = execute
        self.concurrency = concurrency or _positive_env("UX_AUDIT_WORKER_CONCURRENCY", 1)
        self.lease_seconds = lease_seconds or _positive_env("UX_AUDIT_WORKER_LEASE_SEC", 45)
        self.poll_seconds = poll_seconds
        self.worker_id = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._threads: list[threading.Thread] = []
        self._heartbeats: dict[str, float] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._threads:
            return
        self.store.reap_expired()
        for index in range(self.concurrency):
            thread = threading.Thread(target=self._loop, args=(index,), name=f"audit-worker-{index}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self, timeout: float = 5) -> None:
        self._stop.set(); self._wake.set()
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()

    def notify(self) -> None:
        self._wake.set()

    def healthy(self) -> bool:
        return bool(self._threads) and all(thread.is_alive() for thread in self._threads)

    def _loop(self, index: int) -> None:
        worker_id = f"{self.worker_id}-{index}"
        while not self._stop.is_set():
            job = self.store.claim_next(worker_id, self.lease_seconds)
            if not job:
                self._wake.wait(self.poll_seconds); self._wake.clear(); continue
            job_id = str(job["id"])
            heartbeat_stop = threading.Event()
            heartbeat = threading.Thread(target=self._heartbeat, args=(job_id, worker_id, heartbeat_stop), daemon=True)
            heartbeat.start()
            try:
                self.execute(job_id)
                latest = self.store.get(job_id)
                if latest and latest.get("status") == JobStatus.RUNNING:
                    self.store.finish(job_id, worker_id, JobStatus.COMPLETED)
            except Exception:
                self.store.finish(job_id, worker_id, JobStatus.FAILED, error="Audit worker encountered an unexpected error.", failure_class="worker_exception")
            finally:
                heartbeat_stop.set(); heartbeat.join(timeout=1)

    def _heartbeat(self, job_id: str, worker_id: str, stop: threading.Event) -> None:
        interval = max(1.0, self.lease_seconds / 3)
        while not stop.wait(interval):
            if not self.store.heartbeat(job_id, worker_id, self.lease_seconds):
                return


def _positive_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value
