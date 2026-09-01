from __future__ import annotations

import ipaddress
import os
import warnings
from dataclasses import dataclass
from typing import Mapping

import httpx


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    role: str
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"


class AuthenticationError(Exception):
    """A deliberately detail-free authentication failure."""


def _environment() -> str:
    return (os.getenv("APP_ENV") or os.getenv("UX_ENVIRONMENT") or "development").strip().lower()


def _auth_me_url() -> str:
    base = (os.getenv("UX_AUTH_SERVICE_URL") or "http://127.0.0.1:8000/api/v1").rstrip("/")
    return base if base.endswith("/auth/me") else f"{base}/auth/me"


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive number.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive number.")
    return value


def validate_auth_configuration(bind_host: str) -> None:
    if _environment() in {"production", "prod", "staging"} and not os.getenv("UX_AUTH_SERVICE_URL", "").strip():
        raise RuntimeError("UX_AUTH_SERVICE_URL is required outside local development.")
    bypass = os.getenv("UX_DEV_AUTH_BYPASS", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not bypass:
        return
    if _environment() in {"production", "prod", "staging"}:
        raise RuntimeError("UX_DEV_AUTH_BYPASS is forbidden outside local development.")
    try:
        loopback = ipaddress.ip_address(bind_host).is_loopback
    except ValueError:
        loopback = bind_host.lower() == "localhost"
    if not loopback:
        raise RuntimeError("UX_DEV_AUTH_BYPASS requires a loopback-only bind address.")
    warnings.warn(
        "DEVELOPMENT AUTHENTICATION BYPASS IS ACTIVE; never expose this listener.",
        RuntimeWarning,
        stacklevel=2,
    )


def authenticate_bearer(headers: Mapping[str, str]) -> AuthenticatedUser:
    """Validate the portal bearer session through its canonical /auth/me contract."""
    if os.getenv("UX_DEV_AUTH_BYPASS", "0").strip().lower() in {"1", "true", "yes", "on"}:
        return AuthenticatedUser(id="local-development-user", email="local@localhost", role="admin")

    authorization = (headers.get("Authorization") or "").strip()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip() or any(ch.isspace() for ch in token.strip()):
        raise AuthenticationError("Authentication required.")

    timeout = httpx.Timeout(
        connect=_positive_float("UX_AUTH_CONNECT_TIMEOUT_SECONDS", 2.0),
        read=_positive_float("UX_AUTH_READ_TIMEOUT_SECONDS", 5.0),
        write=5.0,
        pool=2.0,
    )
    try:
        response = httpx.get(
            _auth_me_url(),
            headers={"Authorization": f"Bearer {token.strip()}"},
            timeout=timeout,
            follow_redirects=False,
        )
    except (httpx.HTTPError, OSError) as exc:
        raise AuthenticationError("Authentication required.") from exc
    if response.status_code != 200:
        raise AuthenticationError("Authentication required.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthenticationError("Authentication required.") from exc
    user_id = str(payload.get("id") or "").strip()
    email = str(payload.get("email") or "").strip()
    role = str(payload.get("role") or "user").strip().lower()
    is_active = payload.get("is_active") is not False
    if not user_id or not email or not is_active or role not in {"user", "admin"}:
        raise AuthenticationError("Authentication required.")
    return AuthenticatedUser(id=user_id, email=email, role=role, is_active=True)
