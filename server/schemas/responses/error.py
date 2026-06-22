from pydantic import BaseModel

from server.core.exceptions import PrmError
from server.schemas.response_values import ErrorCode


class ErrorResponse(BaseModel):
    detail: str
    code: str

    @classmethod
    def from_prm_error(cls, exc: PrmError) -> "ErrorResponse":
        return cls(detail=exc.message, code=exc.code)

    @classmethod
    def internal_server_error(cls) -> "ErrorResponse":
        return cls(
            detail="Internal server error",
            code=ErrorCode.INTERNAL_SERVER_ERROR,
        )
