from __future__ import annotations

import pytest

from src.security import auth


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_missing_and_invalid_bearer_are_rejected(monkeypatch):
    monkeypatch.delenv("UX_DEV_AUTH_BYPASS", raising=False)
    for headers in ({}, {"Authorization": "Basic nope"}, {"Authorization": "Bearer "}):
        with pytest.raises(auth.AuthenticationError):
            auth.authenticate_bearer(headers)


def test_valid_active_portal_user(monkeypatch):
    monkeypatch.delenv("UX_DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setattr(
        auth.httpx,
        "get",
        lambda *args, **kwargs: Response(200, {"id": "7", "email": "u@example.test", "role": "user", "is_active": True}),
    )
    user = auth.authenticate_bearer({"Authorization": "Bearer opaque-session"})
    assert user.id == "7"
    assert user.role == "user"


@pytest.mark.parametrize("status", [401, 403, 500])
def test_invalid_expired_or_upstream_failure_fails_closed(monkeypatch, status):
    monkeypatch.delenv("UX_DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: Response(status))
    with pytest.raises(auth.AuthenticationError):
        auth.authenticate_bearer({"Authorization": "Bearer opaque-session"})


def test_auth_service_network_failure_fails_closed(monkeypatch):
    monkeypatch.delenv("UX_DEV_AUTH_BYPASS", raising=False)

    def fail(*args, **kwargs):
        raise auth.httpx.ConnectError("unavailable")

    monkeypatch.setattr(auth.httpx, "get", fail)
    with pytest.raises(auth.AuthenticationError):
        auth.authenticate_bearer({"Authorization": "Bearer opaque-session"})


def test_development_bypass_cannot_bind_publicly_or_run_in_production(monkeypatch):
    monkeypatch.setenv("UX_DEV_AUTH_BYPASS", "1")
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(RuntimeError):
        auth.validate_auth_configuration("0.0.0.0")
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        auth.validate_auth_configuration("127.0.0.1")

