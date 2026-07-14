from dataclasses import dataclass

from client.exceptions import SessionNotAuthenticatedError
from server.models.enums import UserRole


@dataclass(frozen=True)
class Session:
    access_token: str
    role: UserRole
    force_password_change: bool
    full_name: str


class SessionManager:
    def __init__(self) -> None:
        self._session: Session | None = None

    @property
    def current(self) -> Session | None:
        return self._session

    def set_session(self, session: Session) -> None:
        self._session = session

    def clear_session(self) -> None:
        self._session = None

    def is_authenticated(self) -> bool:
        return self._session is not None

    def get_role(self) -> UserRole:
        return self._require_session().role

    def get_token(self) -> str:
        return self._require_session().access_token

    def _require_session(self) -> Session:
        if self._session is None:
            raise SessionNotAuthenticatedError("Not logged in")
        return self._session
