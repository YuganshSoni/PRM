from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from server.core.config import Settings
from server.core.exceptions import InvalidTokenError, TokenExpiredError
from server.models.user import User


@dataclass(frozen=True)
class TokenPayload:
    sub: int
    username: str
    role: str
    force_password_change: bool
    exp: int
    iat: int


class JwtTokenService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_access_token(self, user: User) -> str:
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self._settings.jwt_expire_minutes)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "force_password_change": user.force_password_change,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError("Invalid token") from exc

        return TokenPayload(
            sub=int(payload["sub"]),
            username=str(payload["username"]),
            role=str(payload["role"]),
            force_password_change=bool(payload["force_password_change"]),
            exp=int(payload["exp"]),
            iat=int(payload["iat"]),
        )
