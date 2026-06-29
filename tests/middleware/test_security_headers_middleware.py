from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import Response

from server.core.middleware.security_headers_middleware import SecurityHeadersMiddleware


@pytest.mark.asyncio
async def test_sets_security_headers_on_response():
    middleware = SecurityHeadersMiddleware(MagicMock())
    request = MagicMock()
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    call_next.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_does_not_overwrite_existing_security_headers():
    middleware = SecurityHeadersMiddleware(MagicMock())
    request = MagicMock()
    existing = Response("ok")
    existing.headers["X-Frame-Options"] = "SAMEORIGIN"
    call_next = AsyncMock(return_value=existing)

    response = await middleware.dispatch(request, call_next)

    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
