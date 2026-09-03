from __future__ import annotations

import asyncio

from navigator import crawler
from src.audit.discovery import DiscoveredPage, canonical_url, coverage_manifest, merge_candidates, related_site, select_pages, stable_page_id


def test_canonical_identity_stable_and_preserves_meaningful_query():
    assert canonical_url("HTTPS://Example.com/pricing/?utm_source=x") == canonical_url("https://example.com/pricing?utm_source=y")
    assert stable_page_id("https://example.com/product?id=1") != stable_page_id("https://example.com/product?id=2")
    assert canonical_url("https://example.com/fr/products") == "https://example.com/fr/products"


def test_domain_boundary_rejects_prefix_attackers():
    assert related_site("https://www.example.com", "https://docs.example.com")
    assert related_site("https://www.example.co.uk", "https://docs.example.co.uk")
    for hostile in ("https://docs.attacker.test", "https://support.attacker.test", "https://dashboard.attacker.test", "https://example.com.attacker.test", "https://evil-example.com"):
        assert not related_site("https://example.com", hostile)


def test_legal_auth_robots_and_deterministic_page_limit_are_visible():
    pages = merge_candidates([
        {"url": "https://example.test/", "source": "homepage"},
        {"url": "https://example.test/privacy", "source": "footer"},
        {"url": "https://example.test/terms", "source": "footer"},
        {"url": "https://example.test/accessibility", "source": "footer"},
        {"url": "https://example.test/login", "source": "auth_detection"},
        {"url": "https://example.test/blocked", "source": "sitemap"},
    ], "https://example.test", include_auth_pages=False, robots_allowed=lambda url: not url.endswith("blocked"))
    select_pages(pages, 2)
    by_url = {page.canonical_url: page for page in pages}
    assert by_url["https://example.test/login"].exclusion_reason == "auth_disabled"
    assert by_url["https://example.test/blocked"].exclusion_reason == "robots_disallowed"
    assert by_url["https://example.test/privacy"].is_legal
    assert any(page.exclusion_reason == "page_limit" for page in pages)
    manifest = coverage_manifest("audit-1", pages, robots_policy="respect", discovery={}, threshold=0.8)
    assert manifest["summary"]["discovered"] == 6
    assert manifest["summary"]["excluded"] == 4


def test_auth_can_be_explicitly_enabled_and_incomplete_coverage_is_reported():
    pages = merge_candidates([{"url": "https://example.test/login", "source": "auth_detection"}], "https://example.test", include_auth_pages=True)
    select_pages(pages, 1)
    assert pages[0].selection_status == "selected"
    pages[0].selection_status = "failed"; pages[0].failure_reason = "HTTP 404"; pages[0].http_status = 404
    manifest = coverage_manifest("audit-2", pages, robots_policy="respect", discovery={}, threshold=0.8)
    assert manifest["summary"]["coverageStatus"] == "incomplete"
    assert manifest["pages"][0]["failureReason"] == "HTTP 404"


def test_sitemap_urlset_index_duplicates_malformed_and_unsafe_are_bounded(monkeypatch):
    payloads = {
        "https://example.test/sitemap.xml": ("<sitemapindex><sitemap><loc>https://example.test/a.xml</loc></sitemap><sitemap><loc>https://example.test/b.xml</loc></sitemap></sitemapindex>", 200),
        "https://example.test/a.xml": ("<urlset><url><loc>https://example.test/p</loc></url><url><loc>https://example.test/p</loc></url><url><loc>http://127.0.0.1/private</loc></url></urlset>", 200),
        "https://example.test/b.xml": ("<broken", 200),
    }
    async def fake_fetch(_client, url, debug=False): return payloads.get(url, (None, 404))
    monkeypatch.setattr(crawler, "fetch_text", fake_fetch)
    class Checked:
        def __init__(self, url): self.url = url
    def validate(url):
        if "127.0.0.1" in url: raise ValueError("unsafe")
        return Checked(url)
    monkeypatch.setattr(crawler, "validate_public_url", validate)
    urls, limitations = asyncio.run(crawler.parse_sitemaps(None, ["https://example.test/sitemap.xml"], False))
    assert urls == ["https://example.test/p"]
    assert any(item["reason"] == "malformed_sitemap" for item in limitations)
    assert any(item["reason"] == "unsafe_sitemap_location" for item in limitations)
