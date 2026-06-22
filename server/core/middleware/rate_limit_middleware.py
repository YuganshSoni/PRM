import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from server.core.config import Settings
from server.schemas.responses.error import ErrorResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    _WINDOW_SECONDS = 60

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._enabled = settings.rate_limit_enabled
        self._login_limit = settings.rate_limit_login_per_minute
        self._ai_limit = settings.rate_limit_ai_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self._enabled:
            return await call_next(request)

        limit = self._limit_for_path(request.url.path, request.method)
        if limit is None:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.method}:{request.url.path}"
        if self._is_limited(key, limit):
            body = ErrorResponse(
                detail="Too many requests. Please try again later.",
                code="RateLimitExceededError",
            )
            return JSONResponse(status_code=429, content=body.model_dump())

        self._record_hit(key)
        return await call_next(request)

    def _limit_for_path(self, path: str, method: str) -> int | None:
        if method == "POST" and path == "/auth/login":
            return self._login_limit
        if method == "POST" and path == "/ai/skill-match":
            return self._ai_limit
        if method == "POST" and path.startswith("/ai/risk-summary/"):
            return self._ai_limit
        return None

    def _is_limited(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        window_start = now - self._WINDOW_SECONDS
        hits = [timestamp for timestamp in self._hits[key] if timestamp > window_start]
        self._hits[key] = hits
        return len(hits) >= limit

    def _record_hit(self, key: str) -> None:
        self._hits[key].append(time.monotonic())
