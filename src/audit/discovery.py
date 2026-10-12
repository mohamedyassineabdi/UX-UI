"""Deterministic website discovery, sampling, and coverage-manifest primitives."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = frozenset({"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"})
MULTIPART_SUFFIXES = frozenset({"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "co.nz"})
LEGAL_HINTS = ("privacy", "terms", "cookie", "legal", "license", "accessibility", "security", "returns", "shipping")
AUTH_HINTS = ("login", "signin", "sign-in", "signup", "sign-up", "register", "authentication")
# Sitemaps list media and documents alongside pages; these are never audited as pages.
NON_PAGE_EXTENSIONS = frozenset({
    "png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "ico", "bmp", "tif", "tiff",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "zip", "rar", "7z", "gz",
    "mp3", "wav", "ogg", "mp4", "webm", "mov", "avi", "m4v", "json", "xml", "txt", "css", "js",
    "woff", "woff2", "ttf", "otf", "eot",
})


def canonical_url(url: str, *, tracking_parameters: frozenset[str] = TRACKING_PARAMETERS) -> str:
    parsed = urlsplit(str(url).strip())
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower().rstrip(".")
    port = parsed.port
    netloc = hostname if port in (None, 80 if scheme == "http" else 443) else f"{hostname}:{port}"
    path = parsed.path or "/"
    if path != "/": path = path.rstrip("/") or "/"
    query = sorted((key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() not in tracking_parameters)
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


def site_domain(hostname: str) -> str:
    labels = (hostname or "").lower().strip(".").split(".")
    if len(labels) <= 2: return ".".join(labels)
    suffix = ".".join(labels[-2:])
    return ".".join(labels[-3:]) if suffix in MULTIPART_SUFFIXES and len(labels) >= 3 else suffix


def related_site(homepage: str, candidate: str, allowed_hosts: set[str] | None = None) -> bool:
    candidate_host = (urlsplit(candidate).hostname or "").lower()
    if candidate_host in {host.lower() for host in (allowed_hosts or set())}: return True
    return bool(candidate_host) and site_domain(urlsplit(homepage).hostname or "") == site_domain(candidate_host)


def is_page_url(url: str) -> bool:
    """False for media and document files (by path extension); everything else may be a page."""
    last = urlsplit(str(url)).path.rsplit("/", 1)[-1]
    extension = last.rsplit(".", 1)[-1].lower() if "." in last else ""
    return extension not in NON_PAGE_EXTENSIONS


def classify_page(url: str, label: str = "") -> tuple[str, bool, bool]:
    text = f"{url} {label}".lower()
    is_auth = any(token in text for token in AUTH_HINTS)
    is_legal = any(token in text for token in LEGAL_HINTS)
    if is_auth: return "authentication", True, is_legal
    if is_legal: return "legal_or_trust", False, True
    if urlsplit(url).path.rstrip("/") in {"", "/"}: return "homepage", False, False
    return "content", False, False


def stable_page_id(url: str, label: str = "") -> str:
    canonical = canonical_url(url)
    slug = "".join(ch if ch.isalnum() else "-" for ch in (label or urlsplit(canonical).path.strip("/") or "home").lower()).strip("-")[:32] or "home"
    return f"page_{slug}_{hashlib.sha256(canonical.encode()).hexdigest()[:10]}"


@dataclass
class DiscoveredPage:
    requested_url: str
    canonical_url: str
    label: str = ""
    discovery_sources: set[str] = field(default_factory=set)
    page_type: str = "content"
    is_auth: bool = False
    is_legal: bool = False
    is_external: bool = False
    selection_status: str = "discovered"
    selection_reason: str = ""
    exclusion_reason: str = ""
    robots_allowed: bool | None = None
    page_id: str = ""
    collection_status: str = ""
    http_status: int | None = None
    final_url: str = ""
    failure_reason: str = ""
    language: str = ""

    def __post_init__(self) -> None:
        self.canonical_url = canonical_url(self.canonical_url or self.requested_url)
        self.page_id = self.page_id or stable_page_id(self.canonical_url, self.label)
        if self.page_type == "content": self.page_type, self.is_auth, self.is_legal = classify_page(self.canonical_url, self.label)

    def as_dict(self) -> dict:
        return {"pageId": self.page_id, "requestedUrl": self.requested_url, "canonicalUrl": self.canonical_url, "label": self.label, "discoverySources": sorted(self.discovery_sources), "pageType": self.page_type, "isAuth": self.is_auth, "isLegal": self.is_legal, "isExternal": self.is_external, "selectionStatus": self.selection_status, "selectionReason": self.selection_reason, "exclusionReason": self.exclusion_reason, "robotsAllowed": self.robots_allowed, "collectionStatus": self.collection_status, "httpStatus": self.http_status, "finalUrl": self.final_url, "failureReason": self.failure_reason, "language": self.language}


def merge_candidates(candidates: list[dict], homepage: str, *, include_auth_pages: bool, robots_allowed: callable | None = None, allowed_hosts: set[str] | None = None) -> list[DiscoveredPage]:
    pages: dict[str, DiscoveredPage] = {}
    for item in candidates:
        raw = str(item.get("url") or "").strip()
        if not raw: continue
        canonical = canonical_url(raw)
        external = not related_site(homepage, canonical, allowed_hosts)
        page = pages.get(canonical)
        if page is None:
            page = DiscoveredPage(raw, canonical, str(item.get("label") or item.get("name") or ""), set(item.get("sources") or [item.get("source") or "navigation"]), is_external=external)
            pages[canonical] = page
        else:
            page.discovery_sources.update(item.get("sources") or [item.get("source") or "navigation"])
            if not page.label: page.label = str(item.get("label") or item.get("name") or "")
        if not is_page_url(canonical):
            page.selection_status, page.exclusion_reason = "excluded", "not_a_page"
        elif external:
            page.selection_status, page.exclusion_reason = "excluded", "unsupported_external_host"
        elif page.is_auth and not include_auth_pages:
            page.selection_status, page.exclusion_reason = "excluded", "auth_disabled"
        elif robots_allowed is not None:
            page.robots_allowed = bool(robots_allowed(canonical))
            if not page.robots_allowed:
                page.selection_status, page.exclusion_reason = "excluded", "robots_disallowed"
    return sorted(pages.values(), key=lambda p: (p.page_type != "homepage", p.canonical_url))


def navigation_order(menu: dict | None) -> list[str]:
    """Main-menu URLs in display order: top-level items first, then their children."""
    items = (menu or {}).get("navigation") if isinstance(menu, dict) else None
    if not isinstance(items, list):
        return []
    top = [item for item in items if isinstance(item, dict)]
    children = [child for item in top for child in (item.get("children") or []) if isinstance(child, dict)]
    return [str(item["url"]) for item in top + children if item.get("url")]


def select_pages(pages: list[DiscoveredPage], cap: int, navigation_order: list[str] | None = None) -> list[DiscoveredPage]:
    """Select up to `cap` pages: homepage, then main-menu pages (in menu order when known), then the rest."""
    if cap <= 0: raise ValueError("Page cap must be positive.")
    menu_rank = {canonical_url(url): index for index, url in enumerate(navigation_order or [])}
    for page in pages:
        if page.selection_status != "excluded" and not is_page_url(page.canonical_url):
            page.selection_status, page.exclusion_reason = "excluded", "not_a_page"
    eligible = [page for page in pages if page.selection_status != "excluded"]

    def rank(page: DiscoveredPage) -> tuple:
        if page.page_type == "homepage": group = 0
        elif page.page_type == "content" and (page.canonical_url in menu_rank or "navigation" in page.discovery_sources): group = 1
        else: group = {"legal_or_trust": 2, "content": 3, "authentication": 4}.get(page.page_type, 9)
        return (group, menu_rank.get(page.canonical_url, len(menu_rank)), page.canonical_url)

    for page in sorted(eligible, key=rank)[:cap]:
        page.selection_status, page.selection_reason = "selected", "deterministic_representative_sample"
    for page in eligible:
        if page.selection_status == "discovered": page.selection_status, page.exclusion_reason = "excluded", "page_limit"
    return pages


def coverage_manifest(audit_id: str, pages: list[DiscoveredPage], *, robots_policy: str, discovery: dict, threshold: float) -> dict:
    records = [page.as_dict() for page in pages]
    selected = [record for record in records if record["selectionStatus"] in {"selected", "completed", "failed"}]
    completed = [record for record in records if record["selectionStatus"] == "completed"]
    failed = [record for record in records if record["selectionStatus"] == "failed"]
    ratio = len(completed) / len(selected) if selected else 0.0
    return {"schemaVersion": 1, "auditId": audit_id, "discovery": {**discovery, "strategy": "deterministic representative sampling", "robotsPolicy": robots_policy}, "summary": {"discovered": len(records), "selected": len(selected), "completed": len(completed), "failed": len(failed), "excluded": sum(record["selectionStatus"] == "excluded" for record in records), "coverageRatio": ratio, "coverageThreshold": threshold, "coverageStatus": "complete" if selected and ratio >= threshold else "incomplete"}, "pages": records}
