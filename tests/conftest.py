from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.security.auth import AuthenticatedUser


@pytest.fixture
def user_a() -> AuthenticatedUser:
    return AuthenticatedUser(id="user-a", email="a@example.test", role="user")


@pytest.fixture
def user_b() -> AuthenticatedUser:
    return AuthenticatedUser(id="user-b", email="b@example.test", role="user")


@pytest.fixture
def administrator() -> AuthenticatedUser:
    return AuthenticatedUser(id="admin-1", email="admin@example.test", role="admin")


@pytest.fixture
def public_resolver():
    return lambda _host, _port: ["93.184.216.34"]


@dataclass
class FakeRequest:
    url: str


class FakeRoute:
    def __init__(self) -> None:
        self.action = ""

    async def abort(self, _reason: str) -> None:
        self.action = "abort"

    async def continue_(self) -> None:
        self.action = "continue"


class FakeContext:
    def __init__(self) -> None:
        self.handler = None

    async def route(self, _pattern: str, handler) -> None:
        self.handler = handler


@pytest.fixture
def playwright_context() -> FakeContext:
    return FakeContext()

