from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from src.jobs import AuditStorageManager, AuditWorker, JobStatus, JobStore, TransientJobError, retry_transient
from src.main import apply_page_limit
from src.ui import server


def make_job(job_id: str) -> dict[str, str]:
    return {"id": job_id, "type": "website", "inputType": "url", "url": "https://example.test/", "mode": "gtm"}


def test_persistence_owner_report_association_and_restart(tmp_path):
    database = tmp_path / "state" / "jobs.sqlite3"
    store = JobStore(database)
    created = store.create(make_job("job000000001"), owner_id="owner-a", request_id="request-a")
    assert created["status"] == "queued"
    store.update(created["id"], status="running")
    store.update(created["id"], status="completed", resultUrl="/audits/job000000001/")
    store.close()
    restarted = JobStore(database)
    restored = restarted.get_owned("job000000001", "owner-a")
    assert restored and restored["status"] == "completed"
    assert restored["resultUrl"] == "/audits/job000000001/"
    assert restarted.get_owned("job000000001", "owner-b") is None


def test_queued_job_survives_restart_and_expired_running_is_interrupted(tmp_path):
    database = tmp_path / "jobs.sqlite3"
    store = JobStore(database)
    store.create(make_job("job000000002"), owner_id="owner")
    store.close()
    restarted = JobStore(database)
    claim = restarted.claim_next("worker-a", 1)
    assert claim and claim["id"] == "job000000002"
    assert restarted.claim_next("worker-b", 1) is None
    assert restarted.reap_expired(now=time.time() + 2) == ["job000000002"]
    assert restarted.get("job000000002")["status"] == "interrupted"


def test_double_claim_is_atomic(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create(make_job("job000000003"), owner_id="owner")
    barrier = threading.Barrier(3)
    claims: list[object] = []

    def claim(worker: str):
        barrier.wait(); claims.append(store.claim_next(worker, 30))

    threads = [threading.Thread(target=claim, args=(f"worker-{index}",)) for index in range(2)]
    for thread in threads: thread.start()
    barrier.wait()
    for thread in threads: thread.join()
    assert sum(item is not None for item in claims) == 1


def test_bounded_worker_concurrency_and_cancellation(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    for index in range(5):
        store.create(make_job(f"job0000001{index:02d}"), owner_id="owner")
    maximum = 0; active = 0; lock = threading.Lock(); done = threading.Event()

    def execute(job_id: str):
        nonlocal active, maximum
        with lock:
            active += 1; maximum = max(maximum, active)
        time.sleep(0.08)
        store.update(job_id, status="completed", stage="done", progress=100)
        with lock:
            active -= 1
            if sum(store.get(f"job0000001{index:02d}")["status"] == "completed" for index in range(5)) == 5:
                done.set()

    worker = AuditWorker(store, execute, concurrency=2, lease_seconds=10, poll_seconds=0.01)
    worker.start(); assert done.wait(3); worker.stop()
    assert maximum == 2
    queued = store.create(make_job("job000000099"), owner_id="owner")
    cancelled, changed = store.request_cancel(queued["id"])
    assert changed and cancelled and cancelled["status"] == "cancelled"
    assert store.claim_next("another-worker", 30) is None


def test_retention_and_quota_never_remove_active_workspace(tmp_path):
    store = JobStore(tmp_path / "state" / "jobs.sqlite3")
    audits = tmp_path / "audits"
    old = store.create(make_job("job000000004"), owner_id="owner")
    active = store.create(make_job("job000000005"), owner_id="owner")
    store.update(old["id"], status="running"); store.update(old["id"], status="completed")
    (audits / old["id"]).mkdir(parents=True); (audits / old["id"] / "evidence.bin").write_bytes(b"x" * 32)
    (audits / active["id"]).mkdir(parents=True); (audits / active["id"] / "evidence.bin").write_bytes(b"x" * 32)
    manager = AuditStorageManager(store, audits, retention_days=0, max_bytes=40)
    assert manager.cleanup()
    assert not (audits / old["id"]).exists()
    assert (audits / active["id"]).exists()
    assert store.get(old["id"])["artifactsDeleted"] is True


def test_retry_is_bounded_and_only_transient_errors_retry():
    calls = 0
    def transient():
        nonlocal calls
        calls += 1
        if calls < 2: raise TransientJobError("network reset")
        return "ok"
    assert retry_transient(transient, attempts=2, delay=lambda _seconds: None) == "ok"
    assert calls == 2
    with pytest.raises(ValueError):
        retry_transient(lambda: (_ for _ in ()).throw(ValueError("invalid input")), attempts=2, delay=lambda _seconds: None)


def test_maximum_page_limit_is_applied_before_expensive_execution():
    selected, truncated = apply_page_limit([{"url": f"https://example.test/{index}"} for index in range(10)], 3)
    assert len(selected) == 3
    assert truncated == 7


def test_process_timeout_marks_job_failed_and_preserves_workspace(monkeypatch, tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create(make_job("job000000006"), owner_id="owner")
    assert store.claim_next("worker", 30)
    monkeypatch.setattr(server, "JOB_STORE", store)
    monkeypatch.setenv("UX_AUDIT_STAGE_TIMEOUT_SEC", "0.1")
    monkeypatch.setenv("UX_AUDIT_TOTAL_TIMEOUT_SEC", "1")
    workspace = tmp_path / "audits" / job["id"]
    workspace.mkdir(parents=True); (workspace / "evidence.txt").write_text("keep", encoding="utf-8")
    result = server._run_command(job["id"], [server.sys.executable, "-c", "import time; time.sleep(5)"], stage="test timeout", progress=1)
    assert result == -1
    assert store.get(job["id"])["status"] == "failed"
    assert (workspace / "evidence.txt").read_text(encoding="utf-8") == "keep"
