import pytest

from src.audit.measurement import contrast_assessment, target_size_assessment, valid_accessible_name
from src.audit.vlm_schema import validate_visual_response, validate_with_schema_retry


def test_identifiers_are_not_accessible_names():
    assert valid_accessible_name({"id": "save-button", "href": "/settings", "xpathHint": "button#save", "tag": "button"}) == ""
    assert valid_accessible_name({"ariaLabel": "Save"}) == "Save"


def test_target_size_and_contrast_are_conservative():
    assert target_size_assessment({"rect": {"width": 23, "height": 23}, "sufficientSpacing": False})["state"] == "fail"
    assert target_size_assessment({"rect": {"width": 24, "height": 24}})["state"] == "pass"
    assert target_size_assessment({"tag": "a", "inlineText": True, "rect": {"width": 5, "height": 12}})["state"] == "unknown"
    assert contrast_assessment({"complexBackground": True})["measurement"] == "not_measured"
    assert contrast_assessment({"contrastAgainstEffectiveBackground": 3.2, "isLargeText": True})["state"] == "pass"


def test_vlm_schema_rejects_invalid_and_retries_once():
    valid = {"axis_id": "ui_consistency", "title": "Weak hierarchy", "severity": "medium", "confidence": 0.7, "evidence": "Visible labels compete", "recommendation": "Clarify hierarchy"}
    assert validate_visual_response(valid, provider="test", model="test")["measurementClass"] == "ai_visual"
    calls = []
    def malformed_then_valid(_correction):
        calls.append(1)
        return valid if len(calls) == 2 else {"severity": "catastrophic", "confidence": 5}
    result = validate_with_schema_retry(malformed_then_valid, provider="test", model="test")
    assert result["metadata"]["retryCount"] == 1 and result["measurement"] == "measured"
    assert validate_with_schema_retry(lambda _correction: {}, provider="test", model="test")["measurement"] == "collection_failed"
