from src.audit.interaction_classifier import classify_clickable
from src.audit.result_semantics import build_page_index, enrich_result, legacy_status, normalize_result_state


CONFIG = {"classification": {"forbiddenKeywords": ["delete"], "forbiddenHrefKeywords": ["delete"], "safeKeywords": ["open", "ouvrir"]}}


def _cleaned():
    return {"pages": [
        {"name": "Home", "pageId": "page_home", "finalUrl": "https://example.test/", "pageMeta": {"data": {}}},
        {"name": "Duplicate", "pageId": "page_one", "finalUrl": "https://example.test/one", "pageMeta": {"data": {}}},
        {"name": "Duplicate", "pageId": "page_two", "finalUrl": "https://example.test/two", "pageMeta": {"data": {}}},
    ]}


def test_unresolved_provenance_never_falls_back_to_all_audited_pages():
    result = enrich_result({"sheet": "Content", "row": 4, "criterion": "x", "status": "TRUE"}, build_page_index(_cleaned()))
    assert result["provenance"]["status"] == "unresolved"
    assert result["pageRefs"] == []


def test_ambiguous_legacy_name_stays_unresolved_but_page_id_resolves():
    index = build_page_index(_cleaned())
    ambiguous = enrich_result({"criterion": "x", "page_names": ["Duplicate"]}, index)
    exact = enrich_result({"criterion": "x", "pageRefs": ["page_home"]}, index)
    assert ambiguous["provenance"]["status"] == "unresolved"
    assert exact["pageRefs"][0]["pageId"] == "page_home"


def test_site_wide_is_explicit_and_not_claimed_as_all_pages():
    result = enrich_result({"criterion": "x", "siteWide": True, "status": "warning"}, build_page_index(_cleaned()))
    assert result["provenance"]["status"] == "site_wide"
    assert result["provenance"]["scope"] == "site"
    assert result["pageRefs"] == []


def test_state_round_trip_preserves_warning_and_unknown():
    warning = normalize_result_state("warning")
    unknown = normalize_result_state("UNKNOWN")
    assert warning["outcome"] == "warning" and legacy_status(warning) == "WARNING"
    assert unknown == {"outcome": "unknown", "applicability": "applicable", "measurement": "not_measured"}


def test_stable_ids_do_not_include_audit_job_id():
    index = build_page_index(_cleaned())
    first = enrich_result({"criterion": "same", "pageRefs": ["page_home"], "evidence": ["one"]}, index)
    second = enrich_result({"criterion": "same", "pageRefs": ["page_home"], "evidence": ["one"], "jobId": "other"}, index)
    assert first["findingId"] == second["findingId"]
    assert first["evidenceIds"] == second["evidenceIds"]


def test_interaction_default_deny_and_structural_safe_get_are_language_independent():
    assert classify_clickable({"tag": "button", "text": "Ouvrir", "href": ""}, CONFIG)["classification"] == "unknown"
    assert classify_clickable({"tag": "a", "text": "غير مهم", "href": "/catalogue", "target": ""}, CONFIG)["classification"] == "safe"
    assert classify_clickable({"tag": "a", "text": "Open", "href": "/delete", "target": ""}, CONFIG)["classification"] == "forbidden"
    assert classify_clickable({"tag": "input", "type": "submit", "text": "", "href": ""}, CONFIG)["classification"] == "unknown"
