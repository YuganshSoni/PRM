class ClientError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ApiRequestError(ClientError):
    def __init__(self, message: str, *, status_code: int, code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class NetworkError(ClientError):
    pass


class InvalidInputError(ClientError):
    pass


class SessionNotAuthenticatedError(ClientError):
    pass
