from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import Headers
from starlette.responses import Response

from server.core.middleware.request_id_middleware import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
)


def _request(headers: dict[str, str] | None = None) -> MagicMock:
    request = MagicMock()
    request.headers = Headers(headers or {})
    request.state = SimpleNamespace()
    return request


@pytest.mark.asyncio
async def test_generates_request_id_when_header_missing():
    middleware = RequestIdMiddleware(MagicMock())
    request = _request()
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert getattr(request.state, "request_id")
    assert response.headers[REQUEST_ID_HEADER] == request.state.request_id
    call_next.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_reuses_incoming_request_id_header():
    middleware = RequestIdMiddleware(MagicMock())
    request = _request({REQUEST_ID_HEADER.lower(): "req-abc-123"})
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert request.state.request_id == "req-abc-123"
    assert response.headers[REQUEST_ID_HEADER] == "req-abc-123"
