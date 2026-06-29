from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest

from server.core.config import Settings
from server.core.exceptions import InvalidTokenError, TokenExpiredError
from server.core.jwt_token_service import JwtTokenService, TokenPayload


def _settings(**overrides) -> Settings:
    defaults = {
        "database_url": "sqlite:///:memory:",
        "jwt_secret": "a" * 32,
        "jwt_algorithm": "HS256",
        "jwt_expire_minutes": 60,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _user(
    *,
    user_id: int = 1,
    username: str = "alice",
    role_name: str = "ADMIN",
    force_password_change: bool = False,
) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.role.name = role_name
    user.force_password_change = force_password_change
    return user


def test_create_and_decode_access_token():
    service = JwtTokenService(_settings())
    user = _user(force_password_change=True)

    token = service.create_access_token(user)
    payload = service.decode_access_token(token)

    assert isinstance(payload, TokenPayload)
    assert payload.sub == 1
    assert payload.username == "alice"
    assert payload.role == "ADMIN"
    assert payload.force_password_change is True
    assert payload.exp > payload.iat


def test_decode_expired_token_raises_token_expired_error():
    settings = _settings(jwt_expire_minutes=60)
    service = JwtTokenService(settings)
    now = datetime.now(UTC)
    raw = jwt.encode(
        {
            "sub": "7",
            "username": "bob",
            "role": "MANAGER",
            "force_password_change": False,
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenExpiredError, match="Token has expired"):
        service.decode_access_token(raw)


def test_decode_invalid_token_raises_invalid_token_error():
    service = JwtTokenService(_settings())

    with pytest.raises(InvalidTokenError, match="Invalid token"):
        service.decode_access_token("not-a-valid-jwt")


def test_decode_token_signed_with_wrong_secret_raises_invalid_token_error():
    service = JwtTokenService(_settings(jwt_secret="b" * 32))
    other = JwtTokenService(_settings(jwt_secret="c" * 32))
    token = other.create_access_token(_user())

    with pytest.raises(InvalidTokenError, match="Invalid token"):
        service.decode_access_token(token)


def test_create_access_token_embeds_subject_as_string():
    settings = _settings()
    service = JwtTokenService(settings)
    token = service.create_access_token(_user(user_id=42, role_name="RESOURCE"))

    raw = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert raw["sub"] == "42"
    assert raw["role"] == "RESOURCE"
