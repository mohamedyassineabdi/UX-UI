"""Production API plus durable-worker lifecycle coverage for website jobs."""

from __future__ import annotations

import json
import threading

from src.jobs import AuditWorker
from src.ui import server
from test_server_security import api_server, create_audit, request


def test_running_website_job_cancelled_through_api_is_not_completed(api_server, monkeypatch):
    """A real worker must honour an API cancellation after execution has begun."""
    entered = threading.Event()
    release = threading.Event()

    def controlled_audit(job_id: str) -> None:
        entered.set()
        assert release.wait(3)
        # This is the same production cancellation observation used between
        # pipeline stages; no cancellation state is fabricated by the test.
        server._finish_if_cancelled(job_id)

    monkeypatch.setattr(server, "_run_audit_job", controlled_audit)
    worker = AuditWorker(server.JOB_STORE, server._execute_claimed_job, concurrency=1, poll_seconds=0.01)
    monkeypatch.setattr(server, "JOB_WORKER", worker)
    worker.start()
    try:
        audit = create_audit(api_server)
        job_id = audit["id"]
        worker.notify()
        assert entered.wait(3)
        status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/cancel", token="token-a")
        assert status == 200
        assert json.loads(body)["cancelRequested"] is True
        # Non-owners cannot disturb the active job through the same endpoint.
        assert request(api_server, "POST", f"/api/audits/{job_id}/cancel", token="token-b")[0] == 404
        release.set()
        worker.stop()
        persisted = server.JOB_STORE.get(job_id)
        assert persisted and persisted["status"] == "cancelled"
        assert persisted["cancelRequested"] is True
        assert "Audit cancellation requested." in persisted["logs"]
        # A cancelled incomplete job cannot enter the review/publication flow.
        assert request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body={"findingChanges": {}})[0] == 400
    finally:
        release.set()
        worker.stop()
