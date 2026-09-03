from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.ui import server
from src.jobs import AuditStorageManager, JobStore


class PortalAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path != "/api/v1/auth/me" or self.headers.get("Authorization") != "Bearer valid-a":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps({"id": "integration-a", "email": "a@example.test", "role": "user", "is_active": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def call(instance, token=None):
    connection = http.client.HTTPConnection("127.0.0.1", instance.server_port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps({"auditType": "website", "mode": "gtm", "url": "https://example.com/"})
    connection.request("POST", "/api/audits", body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    result = response.status, payload
    connection.close()
    return result


def test_real_auth_me_contract_and_authenticated_api_smoke(monkeypatch, tmp_path):
    auth_server = ThreadingHTTPServer(("127.0.0.1", 0), PortalAuthHandler)
    auth_thread = threading.Thread(target=auth_server.serve_forever, daemon=True)
    auth_thread.start()
    monkeypatch.setenv("UX_AUTH_SERVICE_URL", f"http://127.0.0.1:{auth_server.server_port}/api/v1")
    monkeypatch.delenv("UX_DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setattr(server, "OWNERSHIP_DIR", tmp_path / "ownership")
    monkeypatch.setattr(server, "_validate_url", lambda value: value)
    monkeypatch.setattr(server, "_run_audit_job", lambda _job_id: None)
    store = JobStore(tmp_path / "state" / "jobs.sqlite3")
    monkeypatch.setattr(server, "JOB_STORE", store)
    monkeypatch.setattr(server, "STORAGE_MANAGER", AuditStorageManager(store, tmp_path / "audits", retention_days=0, max_bytes=0))
    server.RATE_LIMITER.clear()

    api_server = ThreadingHTTPServer(("127.0.0.1", 0), server.AuditRequestHandler)
    api_thread = threading.Thread(target=api_server.serve_forever, daemon=True)
    api_thread.start()
    try:
        assert call(api_server)[0] == 401
        assert call(api_server, "expired")[0] == 401
        status, body = call(api_server, "valid-a")
        assert status == 202
        assert json.loads(body)["id"]
    finally:
        api_server.shutdown()
        api_server.server_close()
        auth_server.shutdown()
        auth_server.server_close()
        api_thread.join(timeout=3)
        auth_thread.join(timeout=3)
        store.close()
