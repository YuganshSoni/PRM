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
