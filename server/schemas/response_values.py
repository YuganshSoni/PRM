from enum import StrEnum


class ApiStatus(StrEnum):
    OK = "ok"


class DatabaseConnectionStatus(StrEnum):
    CONNECTED = "connected"


class ErrorCode(StrEnum):
    INTERNAL_SERVER_ERROR = "InternalServerError"


class TokenType(StrEnum):
    BEARER = "bearer"


class AuthMessage(StrEnum):
    LOGOUT_SUCCESS = "Logged out successfully"
    PASSWORD_UPDATED = "Password updated successfully"
