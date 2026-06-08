import logging
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.core.exceptions import (
    ConflictError,
    DatabaseUnavailableError,
    NotFoundError,
    PrmError,
    ValidationError,
)
from server.schemas.responses.error import ErrorResponse

logger = logging.getLogger(__name__)


class ExceptionHandlerRegistrar:
    STATUS_MAP: ClassVar[dict[type[PrmError], int]] = {
        ValidationError: 400,
        NotFoundError: 404,
        ConflictError: 409,
        DatabaseUnavailableError: 503,
    }

    def register(self, app: FastAPI) -> None:
        app.add_exception_handler(PrmError, self.handle_prm_error)
        app.add_exception_handler(Exception, self.handle_unhandled)

    def status_for(self, exc: PrmError) -> int:
        for exc_type, status in self.STATUS_MAP.items():
            if isinstance(exc, exc_type):
                return status
        return 500

    async def handle_prm_error(
        self, _request: Request, exc: PrmError
    ) -> JSONResponse:
        body = ErrorResponse.from_prm_error(exc)
        return JSONResponse(
            status_code=self.status_for(exc),
            content=body.model_dump(),
        )

    async def handle_unhandled(
        self, _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc)
        body = ErrorResponse.internal_server_error()
        return JSONResponse(status_code=500, content=body.model_dump())
