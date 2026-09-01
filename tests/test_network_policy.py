from __future__ import annotations

import asyncio
import pytest

from src.security.network_policy import (
    UnsafeURLError,
    fetch_public_text,
    install_playwright_network_guard,
    validate_public_url,
)
from conftest import FakeRequest, FakeRoute


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://user:pass@example.com/",
        "http://127.0.0.1/",
        "http://127.1/",
        "http://0177.0.0.1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0x7f.0.0.1/",
        "http://%31%32%37.0.0.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://example.com:22/",
        "http://example.com\\@127.0.0.1/",
    ],
)
def test_rejects_unsafe_urls(url, public_resolver):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url, resolver=public_resolver)


def test_normalizes_idn_and_trailing_dot(public_resolver):
    value = validate_public_url("https://EXAMPLE.com./a#fragment", resolver=public_resolver)
    assert value.url == "https://example.com/a"
    assert value.addresses == ("93.184.216.34",)


def test_mixed_public_private_dns_is_rejected():
    resolver = lambda _host, _port: ["93.184.216.34", "10.0.0.7"]
    with pytest.raises(UnsafeURLError):
        validate_public_url("https://example.com/", resolver=resolver)


def test_redirect_to_metadata_is_revalidated_and_blocked(monkeypatch, public_resolver):
    class Headers:
        @staticmethod
        def get_content_charset():
            return "utf-8"

    class Response:
        status = 302
        headers = Headers()

        @staticmethod
        def getheader(name):
            return "http://169.254.169.254/latest/meta-data/" if name == "Location" else None

        @staticmethod
        def read(_size):
            return b""

    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args, **_kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr("src.security.network_policy._PinnedHTTPSConnection", Connection)
    with pytest.raises(UnsafeURLError):
        fetch_public_text("https://example.com/", resolver=public_resolver)


def test_browser_guard_blocks_private_subrequest(monkeypatch, playwright_context, public_resolver):
    allowed = validate_public_url("https://example.com/", resolver=public_resolver)
    asyncio.run(install_playwright_network_guard(playwright_context, [allowed]))
    route = FakeRoute()
    asyncio.run(playwright_context.handler(route, FakeRequest("http://169.254.169.254/latest/meta-data/")))
    assert route.action == "abort"


def test_browser_guard_blocks_dns_rebinding(monkeypatch, playwright_context, public_resolver):
    allowed = validate_public_url("https://example.com/", resolver=public_resolver)
    monkeypatch.setattr("src.security.network_policy._system_resolver", lambda _host, _port: ["127.0.0.1"])
    asyncio.run(install_playwright_network_guard(playwright_context, [allowed]))
    route = FakeRoute()
    asyncio.run(playwright_context.handler(route, FakeRequest("https://example.com/api")))
    assert route.action == "abort"
