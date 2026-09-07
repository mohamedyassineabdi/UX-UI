"""Canonical Phase 2B result state, provenance and stable identity helpers.

This module is deliberately independent of workbook labels.  Legacy TRUE/FALSE/N/A
conversion belongs at the workbook boundary only.
"""
from __future__ import annotations

import hashlib
from typing import Any


OUTCOMES = {"pass", "fail", "warning", "unknown"}
APPLICABILITY = {"applicable", "not_applicable", "unknown"}
MEASUREMENT = {"measured", "not_measured", "collection_failed"}


def stable_id(prefix: str, *parts: Any) -> str:
    canonical = "|".join(" ".join(str(part or "").split()).lower() for part in parts)
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def normalize_result_state(raw: Any, *, applicability: Any = None, measurement: Any = None) -> dict[str, str]:
    value = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    outcome = {
        "true": "pass", "pass": "pass", "passed": "pass", "ok": "pass",
        "false": "fail", "fail": "fail", "failed": "fail",
        "warn": "warning", "warning": "warning",
        "n/a": "unknown", "na": "unknown", "unknown": "unknown", "": "unknown",
    }.get(value, "unknown")
    app = str(applicability or "").strip().lower()
    measured = str(measurement or "").strip().lower()
    if app not in APPLICABILITY:
        app = "not_applicable" if value in {"not_applicable", "n/a", "na"} else "applicable"
    if measured not in MEASUREMENT:
        measured = "not_measured" if outcome == "unknown" else "measured"
    return {"outcome": outcome, "applicability": app, "measurement": measured}


def legacy_status(state: dict[str, str]) -> str:
    """Workbook-only adapter; warning remains visible as WARNING, never FALSE."""
    if state["applicability"] == "not_applicable":
        return "N/A"
    return {"pass": "TRUE", "fail": "FALSE", "warning": "WARNING", "unknown": "UNKNOWN"}[state["outcome"]]


def build_page_index(cleaned: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for page in cleaned.get("pages", []):
        meta = page.get("pageMeta", {}).get("data", {})
        for key in (page.get("pageId"), meta.get("pageId"), page.get("finalUrl"), meta.get("finalUrl"), page.get("url"), meta.get("url"), page.get("name"), meta.get("name")):
            if key:
                index.setdefault(str(key).strip().lower(), []).append(page)
    return index


def page_record(page: dict[str, Any]) -> dict[str, str]:
    meta = page.get("pageMeta", {}).get("data", {})
    shots = meta.get("screenshotPaths", {}) or {}
    return {"pageId": page.get("pageId") or meta.get("pageId") or "", "name": page.get("name") or meta.get("name") or "", "url": page.get("finalUrl") or meta.get("finalUrl") or page.get("url") or meta.get("url") or "", "screenshotPath": shots.get("page") or ""}


def resolve_page_refs(raw_refs: Any, index: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, str]], list[str]]:
    refs = raw_refs if isinstance(raw_refs, list) else ([raw_refs] if raw_refs else [])
    resolved, unresolved, seen = [], [], set()
    for ref in refs:
        key = str(ref.get("pageId") if isinstance(ref, dict) else ref).strip().lower()
        matches = index.get(key, [])
        if len(matches) != 1:
            if key:
                unresolved.append(str(ref))
            continue
        record = page_record(matches[0])
        if record["pageId"] not in seen:
            seen.add(record["pageId"])
            resolved.append(record)
    return resolved, unresolved


def provenance_for(item: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    explicit = item.get("pageRefs") or item.get("source_pages") or item.get("pages") or item.get("page_names") or []
    pages, unresolved = resolve_page_refs(explicit, index)
    site_wide = bool(item.get("siteWide") or str(item.get("scope", "")).lower() == "site")
    methods = item.get("methods") or ([item.get("decision_basis")] if item.get("decision_basis") else [])
    methods = [str(x) for x in methods if x]
    if site_wide:
        status, scope = "site_wide", "site"
    elif pages:
        status, scope = "verified", "page" if len(pages) == 1 else "pages"
    else:
        status, scope = "unresolved", "none"
    return {"status": status, "scope": scope, "methods": methods, "pageRefs": pages, "unresolvedRefs": unresolved}


def enrich_result(item: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out = dict(item)
    state = normalize_result_state(out.get("outcome", out.get("status")), applicability=out.get("applicability"), measurement=out.get("measurement"))
    out.update(state)
    out["rawStatus"] = out.get("rawStatus", out.get("status"))
    out["status"] = legacy_status(state)  # compatibility; consumers should use outcome.
    out["provenance"] = provenance_for(out, index)
    out["pageRefs"] = out["provenance"]["pageRefs"]
    out["source_pages"] = [{"page_name": p["name"], "page_id": p["pageId"], "page_url": p["url"], "screenshot_path": p["screenshotPath"]} for p in out["pageRefs"]]
    primary = out["source_pages"][0] if out["source_pages"] else {}
    out.update({"page_name": primary.get("page_name", ""), "page_id": primary.get("page_id", ""), "page_url": primary.get("page_url", ""), "final_url": primary.get("page_url", ""), "screenshot_path": primary.get("screenshot_path", "")})
    rule = out.get("ruleId") or out.get("machine_criterion") or out.get("criterion") or f"{out.get('sheet','')}:{out.get('row','')}"
    out["ruleId"] = stable_id("rule", rule)
    signature = out.get("findingSignature") or out.get("rationale") or out.get("criterion")
    out["findingId"] = out.get("findingId") or stable_id("finding", out["ruleId"], ",".join(p["pageId"] for p in out["pageRefs"]), signature)
    out["evidenceIds"] = [stable_id("evidence", out["findingId"], value) for value in out.get("evidence", [])]
    return out
