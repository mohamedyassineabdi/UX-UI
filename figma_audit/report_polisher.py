from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field

from figma_audit.config import (
    OLLAMA_API_HOST,
    OLLAMA_API_KEY,
    OLLAMA_REPORT_MODEL,
    OLLAMA_REQUEST_TIMEOUT,
)
from figma_audit.models.criteria import UxUiCriterion
from figma_audit.utils.io import load_json, save_json
from src.audit.vlm_schema import validated_machine_response


CLIENT_COPY_KEYS = ("title", "what_is_wrong", "why_it_matters", "recommended_fix")
REPORT_POLISH_PROMPT_VERSION = "figma_report_polish_v2"


class _PolishedIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=80)
    what_is_wrong: str = Field(min_length=1, max_length=1100)
    why_it_matters: str = Field(min_length=1, max_length=1100)
    recommended_fix: str = Field(min_length=1, max_length=1100)


class _PolishedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issues: list[_PolishedIssue] = Field(min_length=1, max_length=200)


class ReportPolishError(RuntimeError):
    """Raised when client-facing report copy cannot be generated."""


def _safe_text(value: object, max_length: int = 900) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def _compact_issue_payload(
    issue: dict[str, object],
    criterion: UxUiCriterion | None,
) -> dict[str, object]:
    location = issue.get("location") if isinstance(issue.get("location"), dict) else {}
    evidence = issue.get("evidence") if isinstance(issue.get("evidence"), dict) else {}
    subdetector = next(
        (
            evidence.get(key)
            for key in (
                "accessibility_check",
                "task_execution_subdetector",
                "flow_subdetector",
                "ui_consistency_subdetector",
                "visual_brand_subdetector",
                "content_microcopy_subdetector",
            )
            if evidence.get(key)
        ),
        None,
    )

    return {
        "id": issue.get("id"),
        "criterion": issue.get("criterion") or issue.get("axis"),
        "criterion_name": criterion.short_name if criterion else None,
        "criterion_business_impact": criterion.business_impact if criterion else None,
        "criterion_user_impact": criterion.user_impact if criterion else None,
        "default_fix": criterion.default_fix if criterion else None,
        "severity": issue.get("severity"),
        "current_message": issue.get("message"),
        "screen_or_frame": location.get("frame_name") or location.get("node_name"),
        "node_name": location.get("node_name"),
        "visible_text": evidence.get("text_sample"),
        "detector": evidence.get("detector_id"),
        "subdetector": subdetector,
        "confidence": evidence.get("confidence"),
        "contrast_ratio": evidence.get("contrast_ratio"),
        "required_ratio": evidence.get("required_ratio"),
        "confidence_reason": evidence.get("confidence_reason"),
        "plain_language_checks": evidence.get("plain_language_checks"),
        "value_communication_checks": evidence.get("value_communication_checks"),
        "visual_search_checks": evidence.get("visual_search_checks"),
    }


def _normalize_polished_copy(
    *,
    issues: list[dict[str, object]],
    parsed: dict[str, Any],
) -> dict[str, dict[str, str]]:
    raw_items = parsed.get("issues")
    if not isinstance(raw_items, list):
        raise ValueError("Polish response must contain an 'issues' list.")

    issue_ids = {str(issue.get("id")) for issue in issues}
    polished: dict[str, dict[str, str]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        issue_id = str(item.get("id") or "")
        if issue_id not in issue_ids:
            continue
        copy: dict[str, str] = {}
        for key in CLIENT_COPY_KEYS:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                copy[key] = _safe_text(value, 1100)
        if set(copy) == set(CLIENT_COPY_KEYS):
            polished[issue_id] = copy

    return polished


def polish_report_copy_with_ollama(
    *,
    issues: list[dict[str, object]],
    criteria_by_id: dict[str, UxUiCriterion],
    cache_path: Path | None = None,
    force: bool = False,
    log: object = print,
) -> dict[str, dict[str, str]]:
    """
    Rewrite detector findings into client-ready copy using Ollama Cloud.

    The function is intentionally optional. If no API key is configured, callers
    should catch ReportPolishError and continue with deterministic copy.
    """
    if not issues:
        return {}

    if cache_path and cache_path.exists() and not force:
        cached = load_json(cache_path)
        if isinstance(cached, dict) and cached.get("model") == OLLAMA_REPORT_MODEL:
            polished = cached.get("issues")
            if isinstance(polished, dict):
                return {
                    str(issue_id): {
                        key: str(copy[key])
                        for key in CLIENT_COPY_KEYS
                        if isinstance(copy, dict) and key in copy
                    }
                    for issue_id, copy in polished.items()
                    if isinstance(copy, dict)
                    and all(isinstance(copy.get(key), str) for key in CLIENT_COPY_KEYS)
                }

    if not OLLAMA_API_KEY:
        raise ReportPolishError(
            "OLLAMA_API_KEY is not set, so client-facing LLM polishing was skipped."
        )

    compact_issues = []
    for issue in issues:
        criterion_id = str(issue.get("criterion") or issue.get("axis") or "")
        compact_issues.append(_compact_issue_payload(issue, criteria_by_id.get(criterion_id)))

    system_prompt = (
        "You are a senior UX/UI audit writer preparing client-facing report copy. "
        "Rewrite technical findings into concise, professional, business-readable English. "
        "Do not mention detectors, node IDs, JSON, implementation internals, or uncertainty disclaimers. "
        "Do not use emojis or icons. Do not invent facts beyond the provided evidence. "
        "Use simple, informative English that a non-technical stakeholder can understand, "
        "and include enough context that the client knows exactly what to fix."
    )
    user_prompt = {
        "task": "Rewrite each UX/UI finding for a client report.",
        "output_contract": {
            "issues": [
                {
                    "id": "same id as input",
                    "title": "short client-facing issue title, max 80 chars",
                    "what_is_wrong": "1-2 sentences describing the problem visible in the screenshot",
                    "why_it_matters": "1 sentence explaining user/business impact",
                    "recommended_fix": "1-2 sentences with a concrete design fix",
                }
            ]
        },
        "style_rules": [
            "No markdown.",
            "No emojis or decorative icons.",
            "No detector names, node IDs, raw paths, or API language.",
            "Use simple and informative English. Avoid vague statements.",
            "Always name the affected area, visible text, or measured condition when available.",
            "Explain the full context: what is visible, why it creates a user/client problem, and what exact design change is needed.",
            "Keep each field concise enough for a report card.",
        ],
        "issues": compact_issues,
    }

    if callable(log):
        log(f"Polishing report copy with Ollama Cloud model {OLLAMA_REPORT_MODEL}...")

    def fetch(correction: str | None) -> str:
        payload = dict(user_prompt)
        if correction:
            payload["schema_correction"] = correction
        response = requests.post(
            f"{OLLAMA_API_HOST}/api/chat",
            headers={
                "Authorization": f"Bearer {OLLAMA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OLLAMA_REPORT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
            },
            timeout=OLLAMA_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        response_payload = response.json()
        content = (response_payload.get("message") or {}).get("content") if isinstance(response_payload, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama Cloud response did not contain message content.")
        return content
    validated = validated_machine_response(fetch, schema=_PolishedResponse, provider="ollama", model=OLLAMA_REPORT_MODEL, prompt_version=REPORT_POLISH_PROMPT_VERSION)
    if validated["status"] != "completed":
        raise ReportPolishError("Ollama Cloud response failed strict schema validation.")
    polished = _normalize_polished_copy(issues=issues, parsed=validated["result"])

    if not polished:
        raise ReportPolishError("Ollama Cloud returned no usable issue copy.")

    if cache_path:
        save_json(
            cache_path,
            {
                "model": OLLAMA_REPORT_MODEL,
                "issues": polished,
            },
        )

    return polished
