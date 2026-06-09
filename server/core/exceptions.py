class PrmError(Exception):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).__name__


class NotFoundError(PrmError):
    pass


class ConflictError(PrmError):
    pass


class ValidationError(PrmError):
    pass


class DatabaseUnavailableError(PrmError):
    pass


class WeakPasswordError(PrmError):
    pass


class PasswordMismatchError(PrmError):
    pass


class InvalidCredentialsError(PrmError):
    pass


class AccountInactiveError(PrmError):
    pass


class InvalidTokenError(PrmError):
    pass


class TokenExpiredError(PrmError):
    pass


class ForbiddenError(PrmError):
    pass


class UserNotFoundError(PrmError):
    pass


class DuplicateUsernameError(ConflictError):
    pass


class DuplicateEmailError(ConflictError):
    pass


class UserAlreadyInactiveError(ValidationError):
    pass


class UserAlreadyActiveError(ValidationError):
    pass


class SelfOperationForbiddenError(ValidationError):
    pass
