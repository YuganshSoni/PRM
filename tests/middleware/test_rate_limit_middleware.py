from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import JSONResponse, Response

from server.core.middleware.rate_limit_middleware import RateLimitMiddleware


def _settings(
    *,
    enabled: bool = True,
    login_limit: int = 2,
    ai_limit: int = 3,
) -> MagicMock:
    settings = MagicMock()
    settings.rate_limit_enabled = enabled
    settings.rate_limit_login_per_minute = login_limit
    settings.rate_limit_ai_per_minute = ai_limit
    return settings


def _middleware(**kwargs) -> RateLimitMiddleware:
    return RateLimitMiddleware(MagicMock(), _settings(**kwargs))


def test_limit_for_path_login_and_ai_only():
    mw = _middleware(login_limit=5, ai_limit=7)
    assert mw._limit_for_path("/auth/login", "POST") == 5
    assert mw._limit_for_path("/ai/skill-match", "POST") == 7
    assert mw._limit_for_path("/ai/risk-summary/42", "POST") == 7
    assert mw._limit_for_path("/auth/login", "GET") is None
    assert mw._limit_for_path("/projects", "POST") is None


def test_is_limited_when_hits_reach_limit():
    mw = _middleware(login_limit=2)
    key = "127.0.0.1:POST:/auth/login"
    assert mw._is_limited(key, 2) is False
    mw._record_hit(key)
    assert mw._is_limited(key, 2) is False
    mw._record_hit(key)
    assert mw._is_limited(key, 2) is True


@pytest.mark.asyncio
async def test_dispatch_passes_through_when_disabled():
    mw = _middleware(enabled=False)
    request = MagicMock()
    request.url.path = "/auth/login"
    request.method = "POST"
    call_next = AsyncMock(return_value=Response("ok"))

    response = await mw.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)
    assert response.body == b"ok"


@pytest.mark.asyncio
async def test_dispatch_passes_through_unlimited_path():
    mw = _middleware()
    request = MagicMock()
    request.url.path = "/health"
    request.method = "GET"
    call_next = AsyncMock(return_value=Response("ok"))

    await mw.dispatch(request, call_next)
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_returns_429_when_over_limit():
    mw = _middleware(login_limit=1)
    request = MagicMock()
    request.url.path = "/auth/login"
    request.method = "POST"
    request.client = SimpleNamespace(host="10.0.0.1")
    call_next = AsyncMock(return_value=Response("ok"))

    first = await mw.dispatch(request, call_next)
    assert first.body == b"ok"
    second = await mw.dispatch(request, call_next)

    assert isinstance(second, JSONResponse)
    assert second.status_code == 429
    assert call_next.await_count == 1


@pytest.mark.asyncio
async def test_dispatch_uses_unknown_client_when_missing():
    mw = _middleware(login_limit=1)
    request = MagicMock()
    request.url.path = "/auth/login"
    request.method = "POST"
    request.client = None
    call_next = AsyncMock(return_value=Response("ok"))

    await mw.dispatch(request, call_next)
    assert "unknown:POST:/auth/login" in mw._hits
