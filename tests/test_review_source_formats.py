"""The guided editor and immutable snapshots must refer to the same findings."""
import json

import pytest

from src.report.reviewed_report import reviewed_report_context, render_reviewed_report
from src.ui import server
from test_server_security import api_server, create_audit, request


def test_current_deduplicated_findings_keep_reviewer_fields_in_snapshot():
    finding = {"deduplicationId": "defect_123", "title": "Contrast", "evidenceIds": ["e1"]}
    machine = {"deduplicatedFindings": [finding], "priorities": [finding]}
    revision = {"revisionId": "a" * 32, "changes": {"defect_123": {
        "reviewDecision": "confirmed", "reviewNote": "Checked", "priorityOverride": "critical",
        "reviewedRecommendation": "Use <strong>contrast</strong>",
        "suppressed": True, "suppressionReason": "Duplicate",
    }}}
    context = reviewed_report_context(audit_id="audit", machine=machine, revision=revision)
    assert len(context["completeFindings"]) == 1
    assert context["priorities"] == []
    rendered = render_reviewed_report(context)
    # Suppressed findings leave the client report and are listed with their reason.
    assert "Excluded by reviewer" in rendered and "Use &lt;strong&gt;" not in rendered
    assert "Duplicate" in rendered
    assert "review" not in finding  # Never mutate machine data.


def test_generated_priorities_resolve_only_an_exact_unambiguous_finding():
    source = {"title": "Contrast", "evidence": "Measured ratio", "pageUrl": "https://example.test"}
    finding = {**source, "deduplicationId": "defect_123"}
    machine = {"deduplicatedFindings": [finding], "executiveSummary": {"topPriorities": [{**source, "axisId": "accessibility", "axisScore": 30}]}}
    revision = {"changes": {"defect_123": {"suppressed": True, "suppressionReason": "Duplicate"}}}
    assert reviewed_report_context(audit_id="a", machine=machine, revision=revision)["priorities"] == []
    machine["deduplicatedFindings"].append({**source, "deduplicationId": "defect_456"})
    assert len(reviewed_report_context(audit_id="a", machine=machine, revision=revision)["priorities"]) == 1


@pytest.mark.parametrize("kind", ["website", "screenshot", "mobile"])
def test_owner_review_preview_uses_the_mode_specific_source(api_server, kind):
    audit = create_audit(api_server)
    job_id = audit["id"]
    if kind == "website":
        source = server.AuditWorkspace(job_id, server.AUDITS_DIR).gtm_audit
    elif kind == "screenshot":
        server.JOB_STORE.update(job_id, inputType="screenshot")
        source = server.SCREENSHOT_AUDIT_DIR / job_id / "screenshot_gtm_audit.json"
    else:
        # The type is a stored job column, so create the mobile job via its factory.
        original = server.JOB_STORE.get(job_id)
        mobile = server._new_mobile_job("App", "com.example.app", ".MainActivity", "http://127.0.0.1:4723", "Android", "", "")
        mobile.update(ownerId=original["ownerId"], ownerRole=original["ownerRole"])
        server.JOB_STORE.create(mobile, owner_id=original["ownerId"], owner_role=original["ownerRole"])
        job_id = mobile["id"]
        source = server.MOBILE_AUDIT_DIR / job_id / "mobile_gtm_audit.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"findings": [{"findingId": "f1", "title": f"{kind} evidence"}]}), encoding="utf-8")
    status, _, body = request(api_server, "POST", f"/api/audits/{job_id}/revisions", token="token-a", body={"findingChanges": {"f1": {"reviewNote": "Reviewed"}}})
    assert status == 201
    revision = json.loads(body)
    path = f"/api/audits/{job_id}/review-report/{revision['revisionId']}"
    status, _, body = request(api_server, "GET", path, token="token-a")
    assert status == 200 and f"{kind} evidence" in body.decode() and "Reviewed" in body.decode()
    assert request(api_server, "GET", path, token="token-b")[0] == 404


def test_review_source_refuses_symlinks(api_server, monkeypatch):
    job = create_audit(api_server)
    source = server.AuditWorkspace(job["id"], server.AUDITS_DIR).gtm_audit
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"findings": [{"findingId": "f1", "title": "Must not read"}]}), encoding="utf-8")
    monkeypatch.setattr(server, "_contains_symlink", lambda *_args: True)
    context, _ = server._machine_report_context(job["id"], None)
    assert context["findings"] == []
