from __future__ import annotations

import concurrent.futures
import http.client
import ipaddress
import os
import re
import socket
import ssl
from dataclasses import dataclass
from typing import Callable, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit


class UnsafeURLError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedURL:
    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


Resolver = Callable[[str, int], Iterable[str]]


def _system_resolver(hostname: str, port: int) -> Iterable[str]:
    return {item[4][0] for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)}


def _timeout() -> float:
    try:
        return max(0.1, min(float(os.getenv("UX_DNS_TIMEOUT_SECONDS", "3")), 10.0))
    except ValueError:
        return 3.0


def _allowed_ports() -> set[int]:
    raw = os.getenv("UX_ALLOWED_OUTBOUND_PORTS", "80,443")
    try:
        ports = {int(item.strip()) for item in raw.split(",") if item.strip()}
    except ValueError as exc:
        raise RuntimeError("UX_ALLOWED_OUTBOUND_PORTS must contain comma-separated integers.") from exc
    if not ports or any(port < 1 or port > 65535 for port in ports):
        raise RuntimeError("UX_ALLOWED_OUTBOUND_PORTS contains an invalid port.")
    return ports


def _is_public(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
        parsed = parsed.ipv4_mapped
    return bool(parsed.is_global and not (
        parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_multicast
        or parsed.is_reserved or parsed.is_unspecified
    ))


def _canonical_literal(hostname: str) -> str | None:
    candidate = hostname.strip("[]")
    try:
        parsed = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if isinstance(parsed, ipaddress.IPv4Address):
        if candidate != str(parsed):
            raise UnsafeURLError("Ambiguous numeric hostnames are not allowed.")
    return str(parsed)


def validate_public_url(value: str, *, resolver: Resolver | None = None) -> ValidatedURL:
    raw = str(value or "").strip()
    if not raw or any(ord(ch) < 32 for ch in raw) or "\\" in raw:
        raise UnsafeURLError("Enter a valid public website URL.")
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURLError("Only public HTTP and HTTPS URLs are supported.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("URL credentials are not allowed.")
    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError) as exc:
        raise UnsafeURLError("The URL hostname is invalid.") from exc
    if not hostname or len(hostname) > 253 or hostname in {"localhost", "localhost.localdomain"}:
        raise UnsafeURLError("The destination is not public.")
    if "%" in hostname or re.match(r"^(?:0x[0-9a-f]+)(?:\.|$)", hostname, re.IGNORECASE):
        raise UnsafeURLError("Ambiguous numeric hostnames are not allowed.")
    numeric_like = hostname.isdigit() or (
        "." in hostname and all(part.isdigit() or re.fullmatch(r"0x[0-9a-f]+", part, re.IGNORECASE) for part in hostname.split("."))
    )
    literal = _canonical_literal(hostname)
    if numeric_like and literal is None:
        raise UnsafeURLError("Ambiguous numeric hostnames are not allowed.")
    if literal is None:
        labels = hostname.split(".")
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            raise UnsafeURLError("The URL hostname is invalid.")
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise UnsafeURLError("The URL port is invalid.") from exc
    if port not in _allowed_ports():
        raise UnsafeURLError("The destination port is not permitted.")

    if literal:
        addresses = (literal,)
    else:
        resolve = resolver or _system_resolver
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(lambda: tuple(sorted(set(resolve(hostname, port)))))
        try:
            addresses = future.result(timeout=_timeout())
        except (concurrent.futures.TimeoutError, OSError, socket.gaierror) as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise UnsafeURLError("The destination hostname could not be safely resolved.") from exc
        executor.shutdown(wait=False)
    if not addresses or any(not _is_public(address) for address in addresses):
        raise UnsafeURLError("The destination is not public.")

    default_port = 443 if parsed.scheme.lower() == "https" else 80
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = display_host if port == default_port else f"{display_host}:{port}"
    normalized = urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    return ValidatedURL(normalized, hostname, port, tuple(str(ipaddress.ip_address(x)) for x in addresses))


def chromium_host_resolver_rules(validated: Iterable[ValidatedURL]) -> str:
    rules: list[str] = []
    seen: set[str] = set()
    for item in validated:
        if item.hostname in seen:
            continue
        seen.add(item.hostname)
        pinned = f"[{item.addresses[0]}]" if ":" in item.addresses[0] else item.addresses[0]
        rules.append(f"MAP {item.hostname} {pinned}")
    rules.append("EXCLUDE localhost")
    return ",".join(rules)


async def install_playwright_network_guard(context, allowed: Iterable[ValidatedURL]) -> None:
    pins = {item.hostname: set(item.addresses) for item in allowed}

    async def guard(route, request) -> None:
        try:
            checked = validate_public_url(request.url)
            if checked.hostname not in pins or not set(checked.addresses).issubset(pins[checked.hostname]):
                raise UnsafeURLError("Unapproved browser destination.")
        except (UnsafeURLError, ValueError):
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    await context.route("**/*", guard)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, pinned_ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    def connect(self) -> None:
        raw = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host)


def fetch_public_text(
    url: str,
    *,
    resolver: Resolver | None = None,
    max_redirects: int = 3,
    max_bytes: int = 1_048_576,
    timeout: float = 10.0,
) -> tuple[str, str, int]:
    """Fetch through a DNS-pinned verified connection, revalidating every redirect."""
    current = url
    for redirect_count in range(max_redirects + 1):
        checked = validate_public_url(current, resolver=resolver)
        parts = urlsplit(checked.url)
        connection_type = _PinnedHTTPSConnection if parts.scheme == "https" else _PinnedHTTPConnection
        connection = connection_type(checked.hostname, checked.port, checked.addresses[0], timeout)
        path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
        try:
            display_host = f"[{checked.hostname}]" if ":" in checked.hostname else checked.hostname
            host_header = display_host if checked.port in {80, 443} else f"{display_host}:{checked.port}"
            connection.request(
                "GET",
                path,
                headers={"Host": host_header, "User-Agent": "UXUI-Auditor/1.0", "Accept": "text/html,text/plain"},
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                response.read(4096)
                if not location or redirect_count >= max_redirects:
                    raise UnsafeURLError("The redirect chain is invalid or too long.")
                current = urljoin(checked.url, location)
                continue
            content_length = response.getheader("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise UnsafeURLError("The remote response is too large.")
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise UnsafeURLError("The remote response is too large.")
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="replace"), checked.url, response.status
        finally:
            connection.close()
    raise UnsafeURLError("The redirect chain is too long.")
