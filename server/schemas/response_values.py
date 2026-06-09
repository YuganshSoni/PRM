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


class UserMessage(StrEnum):
    ACCOUNT_CREATED = (
        "Account created. User must change password on first login."
    )
    PASSWORD_RESET = (
        "Password reset. User will be prompted to change it on next login."
    )
    USER_DEACTIVATED = "User deactivated."
    USER_REACTIVATED = "Account reactivated."
