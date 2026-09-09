import json
import hashlib

from test_server_security import api_server, create_audit, request


def _change(expected=None, **fields):
    body = {"findingChanges": {"finding_1": fields or {"reviewNote": "Needs confirmation"}}}
    if expected is not None: body["expectedRevisionId"] = expected
    return body


def test_revision_history_conflict_and_edit_is_not_validation(api_server):
    audit = create_audit(api_server); job_id = audit["id"]
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body=_change())
    assert status == 201
    first = json.loads(body); assert first["reviewStatus"] == "in_review"
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body=_change(first["revisionId"], reviewNote="Second review"))
    assert status == 201
    second = json.loads(body); assert second["baseRevisionId"] == first["revisionId"]
    assert request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body=_change(first["revisionId"], reviewNote="stale"))[0] == 409
    review = json.loads(request(api_server, "GET", f"/api/audits/{job_id}/review", token="token-a")[2])
    assert len(review["revisions"]) == 2 and review["reviewStatus"] == "in_review"


def test_machine_fields_and_critical_suppression_require_structured_valid_values(api_server):
    audit = create_audit(api_server); path = f"/api/audits/{audit['id']}/revisions"
    assert request(api_server, "POST", path, token="token-a", body={"findingChanges": {"f": {"ruleId": "rewrite"}}})[0] == 400
    assert request(api_server, "POST", path, token="token-a", body={"findingChanges": {"f": {"suppressed": True}}})[0] == 400
    assert request(api_server, "POST", path, token="token-a", body={"findingChanges": {"f": {"suppressed": True, "suppressionReason": "duplicate confirmed by reviewer"}}})[0] == 201


def test_review_ownership_and_explicit_validation(api_server):
    audit = create_audit(api_server); job_id = audit["id"]; path = f"/api/audits/{job_id}/revisions"
    revision = json.loads(request(api_server, "POST", path, token="token-a", body=_change())[2])
    assert request(api_server, "GET", f"/api/audits/{job_id}/review", token="token-b")[0] == 404
    assert request(api_server, "POST", f"/api/audits/{job_id}/validate", token="token-b", body={"revisionId": revision["revisionId"]})[0] == 404
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/validate", token="token-a", body={"revisionId": revision["revisionId"]})
    assert status == 200 and json.loads(body)["validatedAt"]
    # A post-validation edit is a new in-review revision; the validated entry is immutable.
    follow_up = json.loads(request(api_server, "POST", path, token="token-a", body=_change(revision["revisionId"], reviewNote="post validation edit"))[2])
    assert follow_up["reviewStatus"] == "in_review" and follow_up["baseRevisionId"] == revision["revisionId"]


def test_publication_binds_explicit_validated_revision(api_server, monkeypatch):
    audit = create_audit(api_server); job_id = audit["id"]; path = f"/api/audits/{job_id}/revisions"
    server = __import__("src.ui.server", fromlist=["server"])
    server.JOB_STORE.update(job_id, status="running"); server.JOB_STORE.update(job_id, status="completed")
    monkeypatch.setattr(server, "_publish_job_report", lambda *_args: "https://example.test/publication/a")
    first = json.loads(request(api_server, "POST", path, token="token-a", body=_change())[2])
    request(api_server, "POST", f"/api/audits/{job_id}/validate", token="token-a", body={"revisionId": first["revisionId"]})
    second = json.loads(request(api_server, "POST", path, token="token-a", body=_change(first["revisionId"], reviewNote="new unvalidated edit"))[2])
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/publish", token="token-a", body={"revisionId": first["revisionId"]})
    publication = json.loads(body)["publication"]
    assert status == 200 and publication["revisionId"] == first["revisionId"] and publication["publicationStatus"] == "succeeded"
    assert second["revisionId"] != publication["revisionId"]
    assert request(api_server, "POST", f"/api/audits/{job_id}/publish", token="token-a", body={"revisionId": second["revisionId"]})[0] == 409


def test_reviewed_report_preserves_complete_findings_and_escapes_reviewer_text():
    from src.report.reviewed_report import render_reviewed_report, reviewed_report_context
    findings = [{"findingId": f"f{i}", "ruleId": f"r{i}", "outcome": "fail", "evidenceIds": [f"e{i}"], "title": f"Finding {i}"} for i in range(10)]
    machine = {"findings": findings, "priorities": findings[:3], "summary": {"coverageRatio": 0.9}, "executiveSummary": {"overallCoverage": 0.8}}
    revision = {"revisionId": "a" * 32, "reviewStatus": "validated", "reviewerId": "reviewer", "changes": {"f4": {"suppressed": True, "suppressionReason": "duplicate", "reviewNote": "<script>alert(1)</script>"}}}
    context = reviewed_report_context(audit_id="audit", machine=machine, revision=revision)
    report = render_reviewed_report(context)
    assert len(context["priorities"]) == 3 and len(context["completeFindings"]) == 10
    assert "Suppressed from executive priorities: duplicate" in report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report and "<script>alert(1)</script>" not in report
    assert "Collection coverage" in report and "Measurement coverage" in report and "Methodology" in report and "Limitations" in report


def test_publication_snapshot_hash_is_immutable(api_server, monkeypatch):
    audit = create_audit(api_server); server = __import__("src.ui.server", fromlist=["server"]); job_id = audit["id"]
    server.JOB_STORE.update(job_id, status="running"); server.JOB_STORE.update(job_id, status="completed")
    monkeypatch.setattr(server, "_publish_job_report", lambda *_args: "https://example.test/snapshot")
    published = json.loads(request(api_server, "POST", f"/api/audits/{job_id}/publish", token="token-a", body={})[2])["publication"]
    snapshot = published["snapshot"]; path = server.AuditWorkspace(job_id, server.AUDITS_DIR).root / snapshot["snapshotPath"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == snapshot["snapshotHash"]
    assert "not reviewed" in path.read_text(encoding="utf-8")


def test_historical_reviewed_publication_remains_bound_to_its_snapshot(api_server, monkeypatch):
    audit = create_audit(api_server); server = __import__("src.ui.server", fromlist=["server"]); job_id = audit["id"]
    server.JOB_STORE.update(job_id, status="running"); server.JOB_STORE.update(job_id, status="completed")
    monkeypatch.setattr(server, "_publish_job_report", lambda *_args: "https://example.test/reviewed")
    path = f"/api/audits/{job_id}/revisions"
    revision_a = json.loads(request(api_server, "POST", path, token="token-a", body=_change(reviewNote="A"))[2])
    assert request(api_server, "POST", f"/api/audits/{job_id}/validate", token="token-a", body={"revisionId": revision_a["revisionId"]})[0] == 200
    publication_a = json.loads(request(api_server, "POST", f"/api/audits/{job_id}/publish", token="token-a", body={"revisionId": revision_a["revisionId"]})[2])["publication"]
    snapshot_a = publication_a["snapshot"]
    file_a = server.AuditWorkspace(job_id, server.AUDITS_DIR).root / snapshot_a["snapshotPath"]
    original_html, original_hash = file_a.read_bytes(), snapshot_a["snapshotHash"]
    revision_b = json.loads(request(api_server, "POST", path, token="token-a", body=_change(revision_a["revisionId"], reviewNote="B"))[2])
    assert request(api_server, "POST", f"/api/audits/{job_id}/validate", token="token-a", body={"revisionId": revision_b["revisionId"]})[0] == 200
    assert request(api_server, "POST", f"/api/audits/{job_id}/publish", token="token-a", body={"revisionId": revision_b["revisionId"]})[0] == 200
    assert file_a.read_bytes() == original_html
    assert hashlib.sha256(file_a.read_bytes()).hexdigest() == original_hash
    assert publication_a["revisionId"] == revision_a["revisionId"] != revision_b["revisionId"]


def test_other_owner_cannot_approve_publish_or_read_reviewed_report(api_server):
    audit = create_audit(api_server); job_id = audit["id"]
    revision = json.loads(request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body=_change())[2])
    cases = (("POST", f"/api/audits/{job_id}/approve", {"revisionId": revision["revisionId"]}), ("POST", f"/api/audits/{job_id}/publish", {"revisionId": revision["revisionId"]}), ("GET", f"/api/audits/{job_id}/review-report/{revision['revisionId']}", None))
    for method, request_path, body in cases:
        assert request(api_server, method, request_path, token="token-b", body=body)[0] == 404
