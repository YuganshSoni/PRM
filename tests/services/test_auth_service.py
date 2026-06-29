from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    AccountInactiveError,
    InvalidCredentialsError,
    PasswordMismatchError,
    WeakPasswordError,
)
from server.models.enums import UserStatus
from server.services.auth_service import AuthService, ChangePasswordResult, LoginResult


def _service(
    *,
    user_repository=None,
    password_hasher=None,
    jwt_token_service=None,
    password_policy=None,
) -> AuthService:
    return AuthService(
        user_repository=user_repository or AsyncMock(),
        password_hasher=password_hasher or MagicMock(),
        jwt_token_service=jwt_token_service or MagicMock(),
        password_policy=password_policy or MagicMock(),
    )


def _active_user() -> MagicMock:
    user = MagicMock()
    user.username = "alice"
    user.status = UserStatus.ACTIVE
    user.password_hash = "hashed"
    user.force_password_change = True
    return user


@pytest.mark.asyncio
async def test_login_returns_token_and_user_on_success():
    user = _active_user()
    repo = AsyncMock()
    repo.find_by_username.return_value = user
    hasher = MagicMock()
    hasher.verify.return_value = True
    jwt_service = MagicMock()
    jwt_service.create_access_token.return_value = "token-abc"

    result = await _service(
        user_repository=repo,
        password_hasher=hasher,
        jwt_token_service=jwt_service,
    ).login("alice", "SecretPass1")

    assert isinstance(result, LoginResult)
    assert result.access_token == "token-abc"
    assert result.user is user
    repo.find_by_username.assert_awaited_once_with("alice")
    hasher.verify.assert_called_once_with("SecretPass1", "hashed")
    jwt_service.create_access_token.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_login_raises_when_user_not_found():
    repo = AsyncMock()
    repo.find_by_username.return_value = None

    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        await _service(user_repository=repo).login("missing", "SecretPass1")


@pytest.mark.asyncio
async def test_login_raises_when_account_inactive():
    user = _active_user()
    user.status = UserStatus.INACTIVE
    repo = AsyncMock()
    repo.find_by_username.return_value = user

    with pytest.raises(AccountInactiveError, match="Account is inactive"):
        await _service(user_repository=repo).login("alice", "SecretPass1")


@pytest.mark.asyncio
async def test_login_raises_when_password_incorrect():
    user = _active_user()
    repo = AsyncMock()
    repo.find_by_username.return_value = user
    hasher = MagicMock()
    hasher.verify.return_value = False

    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        await _service(user_repository=repo, password_hasher=hasher).login(
            "alice", "wrong"
        )


def test_validate_password_strength_delegates_to_policy():
    policy = MagicMock()
    service = _service(password_policy=policy)

    service.validate_password_strength("SecretPass1")

    policy.validate.assert_called_once_with("SecretPass1")


@pytest.mark.asyncio
async def test_change_password_updates_hash_and_returns_token():
    user = _active_user()
    repo = AsyncMock()
    hasher = MagicMock()
    hasher.hash.return_value = "new-hash"
    jwt_service = MagicMock()
    jwt_service.create_access_token.return_value = "new-token"
    policy = MagicMock()

    result = await _service(
        user_repository=repo,
        password_hasher=hasher,
        jwt_token_service=jwt_service,
        password_policy=policy,
    ).change_password(user, "NewPass12", "NewPass12")

    assert isinstance(result, ChangePasswordResult)
    assert result.access_token == "new-token"
    assert result.user is user
    assert user.password_hash == "new-hash"
    assert user.force_password_change is False
    policy.validate.assert_called_once_with("NewPass12")
    hasher.hash.assert_called_once_with("NewPass12")
    repo.save.assert_awaited_once_with(user)
    jwt_service.create_access_token.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_change_password_raises_on_mismatch():
    user = _active_user()

    with pytest.raises(PasswordMismatchError, match="Passwords do not match"):
        await _service().change_password(user, "NewPass12", "OtherPass1")


@pytest.mark.asyncio
async def test_change_password_raises_on_weak_password():
    user = _active_user()
    policy = MagicMock()
    policy.validate.side_effect = WeakPasswordError("too weak")
    repo = AsyncMock()
    hasher = MagicMock()

    with pytest.raises(WeakPasswordError, match="too weak"):
        await _service(
            user_repository=repo,
            password_hasher=hasher,
            password_policy=policy,
        ).change_password(user, "weak", "weak")

    repo.save.assert_not_awaited()
    hasher.hash.assert_not_called()
