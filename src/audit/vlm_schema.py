"""Strict, versioned validation for machine-consumed visual findings."""
from __future__ import annotations

from time import perf_counter
import json
import re
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

PROMPT_VERSION = "gtm_visual_v2"
SCHEMA_VERSION = "1"
T = TypeVar("T", bound=BaseModel)


class VisualFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    axis_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    severity: str
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(min_length=1, max_length=1200)
    recommendation: str = Field(min_length=1, max_length=1200)

    def model_post_init(self, __context: Any) -> None:
        if self.severity not in {"low", "medium", "high"}:
            raise ValueError("invalid severity")


def validate_visual_response(payload: dict[str, Any], *, provider: str, model: str, retry_count: int = 0, started_at: float | None = None) -> dict[str, Any]:
    finding = VisualFinding.model_validate(payload)
    return {**finding.model_dump(), "measurement": "measured", "measurementMethod": "vlm", "measurementClass": "ai_visual", "metadata": {"provider": provider, "model": model, "promptVersion": PROMPT_VERSION, "schemaVersion": SCHEMA_VERSION, "retryCount": retry_count, "validationStatus": "valid", "durationMs": round((perf_counter() - started_at) * 1000) if started_at else None}}


def validate_with_schema_retry(fetch: Callable[[str | None], dict[str, Any]], *, provider: str, model: str) -> dict[str, Any]:
    started = perf_counter()
    for retry in range(2):
        try:
            return validate_visual_response(fetch("Return the required schema only." if retry else None), provider=provider, model=model, retry_count=retry, started_at=started)
        except (ValidationError, ValueError, TypeError):
            continue
    return {"measurement": "collection_failed", "measurementMethod": "vlm", "measurementClass": "ai_visual", "metadata": {"provider": provider, "model": model, "promptVersion": PROMPT_VERSION, "schemaVersion": SCHEMA_VERSION, "retryCount": 1, "validationStatus": "failed", "durationMs": round((perf_counter() - started) * 1000)}}


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a model JSON object without accepting arbitrary prose as data."""
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(content[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object.")
    return value


def validated_machine_response(
    fetch: Callable[[str | None], str], *, schema: type[T], provider: str, model: str,
    prompt_version: str, disabled: bool = False,
) -> dict[str, Any]:
    """One bounded schema-correction retry, separate from provider transport retries.

    Callers keep their provider client; this gateway owns only parsing, schema
    validation and the portable metadata/failure state required by audit JSON.
    """
    started = perf_counter()
    if disabled:
        return {"measurement": "not_measured", "status": "disabled", "result": None,
                "metadata": {"provider": provider, "model": model, "promptVersion": prompt_version,
                             "schemaVersion": SCHEMA_VERSION, "durationMs": 0, "retryCount": 0,
                             "validationStatus": "disabled"}}
    for retry_count in range(2):
        try:
            correction = None if retry_count == 0 else "Your previous response was invalid. Return only the required JSON schema with every required field."
            result = schema.model_validate(parse_json_object(fetch(correction))).model_dump()
            return {"measurement": "measured", "status": "completed", "result": result,
                    "metadata": {"provider": provider, "model": model, "promptVersion": prompt_version,
                                 "schemaVersion": SCHEMA_VERSION, "durationMs": round((perf_counter() - started) * 1000),
                                 "retryCount": retry_count, "validationStatus": "valid"}}
        except (ValidationError, ValueError, TypeError):
            continue
        except Exception:
            # Transport failures are already retried by the provider client.
            break
    return {"measurement": "collection_failed", "status": "failed", "result": None,
            "metadata": {"provider": provider, "model": model, "promptVersion": prompt_version,
                         "schemaVersion": SCHEMA_VERSION, "durationMs": round((perf_counter() - started) * 1000),
                         "retryCount": 1, "validationStatus": "failed"}}
