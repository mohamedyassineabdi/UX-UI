"""Small, framework-neutral response and JSON-body helpers for the UI server."""

from __future__ import annotations

import json
import mimetypes
import shutil
from http import HTTPStatus
from pathlib import Path
from typing import Any


def send_json(handler: Any, payload: Any, status: HTTPStatus, headers: dict[str, str] | None = None) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    for name, value in (headers or {}).items():
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(body)


def send_file(handler: Any, file_path: Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
        content_type = f"{content_type}; charset=utf-8"
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(file_path.stat().st_size))
    handler.send_header("Cache-Control", "public, max-age=300")
    handler.end_headers()
    with file_path.open("rb") as source:
        shutil.copyfileobj(source, handler.wfile, length=64 * 1024)
    handler.wfile.flush()


def read_json_body(handler: Any, *, max_json_bytes: int, max_discard_bytes: int) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length < 0 or length > max_json_bytes:
        if 0 < length <= max_discard_bytes:
            handler.rfile.read(length)
        raise ValueError(f"JSON request exceeds the {max_json_bytes}-byte limit.")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    return data
