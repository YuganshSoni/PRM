from enum import StrEnum


class ApiStatus(StrEnum):
    OK = "ok"


class DatabaseConnectionStatus(StrEnum):
    CONNECTED = "connected"


class ErrorCode(StrEnum):
    INTERNAL_SERVER_ERROR = "InternalServerError"
