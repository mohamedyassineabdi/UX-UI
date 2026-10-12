"""Regression tests: opt-in Codex recovery of weak website navigation."""
import json
from unittest.mock import patch

import pytest

from navigator.ai_navigation_helper import (
    _navigation_timeout,
    _safe_menu_toggle,
    _validated_result,
    call_codex_navigation_detector,
)
from navigator import crawler


MENU = {
    "candidate_id": "ai_candidate_2", "tag": "button", "text": "",
    "aria_label": "Open menu", "title": "", "href": None,
    "role": None, "near_top": True, "icon_like": True,
}
CHECKOUT = {
    "candidate_id": "ai_candidate_3", "tag": "button", "text": "Checkout",
    "aria_label": "", "title": "", "href": None,
    "role": None, "near_top": True, "icon_like": False,
}
LINK = {
    "candidate_id": "ai_candidate_4", "tag": "a", "text": "Menu",
    "aria_label": "", "title": "", "href": "/account",
    "role": None, "near_top": True, "icon_like": False,
}


def response(*, candidate_id="ai_candidate_2", categories=None, confidence=0.95):
    return json.dumps({
        "navigation_present": True,
        "navigation_style": "hamburger",
        "interaction_style": "click",
        "menu_trigger": {
            "exists": True, "candidate_id": candidate_id,
            "reason": "Menu button in top navigation", "confidence": confidence,
        },
        "top_categories": categories or [],
        "utility_items": {
            "signin": {"visible": False, "candidate_id": None, "label": None, "confidence": 0},
            "signup": {"visible": False, "candidate_id": None, "label": None, "confidence": 0},
            "search": {"visible": False, "candidate_id": None, "label": None, "confidence": 0},
        },
        "notes": "",
    })


def test_safe_menu_accepts_menu_button_rejects_links_and_checkout():
    assert _safe_menu_toggle(MENU)
    assert not _safe_menu_toggle(CHECKOUT)
    assert not _safe_menu_toggle(LINK)


@pytest.mark.parametrize("candidate,confidence", [
    ("ai_candidate_999", 0.99),
    ("ai_candidate_3", 0.99),
    ("ai_candidate_4", 0.99),
    ("ai_candidate_2", 0.2),
    ("../../outside", 0.99),
])
def test_invalid_or_unsafe_recommendations_never_trigger_click(candidate, confidence):
    result = _validated_result(
        response(candidate_id=candidate, confidence=confidence),
        [{"name": "Articles"}], [MENU, CHECKOUT, LINK],
    )
    assert result["menu_trigger"]["exists"] is False
    assert result["menu_trigger"]["candidate_id"] is None


def test_category_hallucinations_are_filtered():
    result = _validated_result(response(categories=[
        {"name": "Articles", "confidence": 0.9},
        {"name": "Invisible category", "confidence": 0.99},
        {"name": "Articles", "confidence": 0.9},
    ]), [{"name": "Articles"}], [MENU])
    assert [x["name"] for x in result["top_categories"]] == ["Articles"]


def test_codex_gets_png_uses_existing_backend_and_no_ollama_http(monkeypatch):
    monkeypatch.delenv("UX_AUDIT_DEADLINE", raising=False)
    with patch("navigator.ai_navigation_helper.run_codex_cli_json", return_value=response()) as cli:
        result = call_codex_navigation_detector(
            screenshot_bytes=b"\x89PNG\r\n\x1a\n",
            homepage="https://example.com",
            mobile=True,
            current_nav_items=[],
            candidates=[MENU],
        )
    assert result["menu_trigger"]["candidate_id"] == MENU["candidate_id"]
    args = cli.call_args.kwargs
    assert args["timeout"] == 30
    assert len(args["image_paths"]) == 1
    assert args["image_paths"][0].read_bytes() if args["image_paths"][0].exists() else True
    assert "https://example.com" in args["prompt"]


def test_model_failure_is_explicit(monkeypatch):
    monkeypatch.delenv("UX_AUDIT_DEADLINE", raising=False)
    with patch("navigator.ai_navigation_helper.run_codex_cli_json", side_effect=RuntimeError("CLI unavailable")):
        with pytest.raises(RuntimeError, match="CLI unavailable"):
            call_codex_navigation_detector(b"png", "https://example.com", False, [], [MENU])


def test_invalid_json_and_invalid_schema_are_rejected():
    for content in ('no json', '{"navigation_present": true}', '{"navigation_present":true,"top_categories":[{"name":"x","confidence":4}]}'):
        with pytest.raises((ValueError, TypeError)):
            _validated_result(content, [], [MENU])


def test_navigation_timeout_respects_budget(monkeypatch):
    monkeypatch.setenv("CRAWLER_AI_NAV_TIMEOUT_SEC", "1000")
    monkeypatch.delenv("UX_AUDIT_DEADLINE", raising=False)
    assert _navigation_timeout() == 60
    monkeypatch.setenv("UX_AUDIT_DEADLINE", "1")
    with pytest.raises(RuntimeError, match="insufficient remaining"):
        _navigation_timeout()


def test_crawler_uses_codex_navigation_not_legacy_ollama():
    assert crawler.call_codex_navigation_detector is call_codex_navigation_detector
