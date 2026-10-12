"""The client report is served to its owner only and is what deployed snapshots contain."""
import http.client
import json

from client_report_fixtures import machine
from src.ui import server
from test_server_security import api_server, create_audit, request  # noqa: F401


def seeded(api_server):
    job_id = create_audit(api_server)["id"]
    source = server.AuditWorkspace(job_id, server.AUDITS_DIR).gtm_audit
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(machine()), encoding="utf-8")
    return job_id


def test_owner_gets_the_client_report_with_a_strict_policy(api_server):
    job_id = seeded(api_server)
    status, headers, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report", token="token-a")
    assert status == 200 and 'id="executive-summary"' in body.decode() and "managers.tn" in body.decode()
    assert headers["Cache-Control"] == "no-store" and headers["Content-Type"].startswith("text/html")
    connection = http.client.HTTPConnection("127.0.0.1", api_server.server_port, timeout=5)
    connection.request("GET", f"/api/audits/{job_id}/client-report", headers={"Authorization": "Bearer token-a"})
    response = connection.getresponse(); response.read(); connection.close()
    policies = [value for name, value in response.getheaders() if name.lower() == "content-security-policy"]
    assert any(policy.startswith("default-src 'none'") for policy in policies)


def test_other_owner_cannot_read_the_client_report(api_server):
    job_id = seeded(api_server)
    assert request(api_server, "GET", f"/api/audits/{job_id}/client-report", token="token-b")[0] == 404


def test_unknown_revision_is_not_found(api_server):
    job_id = seeded(api_server)
    assert request(api_server, "GET", f"/api/audits/{job_id}/client-report?revision=nope", token="token-a")[0] == 404


def test_revision_edits_appear_in_the_client_report(api_server):
    job_id = seeded(api_server)
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a",
                              body={"findingChanges": {"d1": {"reviewNote": "Seen on checkout too"}}})
    assert status == 201
    revision_id = json.loads(body)["revisionId"]
    status, _, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report?revision={revision_id}", token="token-a")
    assert status == 200 and "Reviewer note: Seen on checkout too" in body.decode()


def test_snapshot_context_is_image_free_json(api_server):
    job_id = seeded(api_server)
    context, rendered = server._machine_report_context(job_id, None)
    assert 'id="cover"' in rendered and "data:image" not in json.dumps(context)


def test_embedded_view_leaves_the_call_to_action_to_the_app(api_server, monkeypatch):
    from src.report.client import render
    payload = {"bookingUrl": "https://cal.example/x", "expert": {"name": "E", "title": "T"}, "counts": {},
               "copy": {"eyebrow": "e", "heading": "h", "body": "b", "cleanHeading": "h", "cleanBody": "b", "cta": "Book"}}
    monkeypatch.setattr(render, "teaser_payload", lambda *a, **k: payload)
    job_id = seeded(api_server)
    full = request(api_server, "GET", f"/api/audits/{job_id}/client-report", token="token-a")[2].decode()
    embedded = request(api_server, "GET", f"/api/audits/{job_id}/client-report?embed=1", token="token-a")[2].decode()
    assert 'id="next-steps"' in full and 'id="next-steps"' not in embedded
    assert "fonts.googleapis.com" in full and "fonts.googleapis.com" not in embedded  # the app CSP blocks web fonts
    assert "fonts.googleapis.com" in full and "fonts.googleapis.com" not in embedded  # the app CSP blocks web fonts
