from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    SelfOperationForbiddenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
    ValidationError,
    WeakPasswordError,
)
from server.models.enums import UserRole, UserStatus
from server.schemas.requests.user import CreateUserRequest
from server.services.user_service import UserService


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def role_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def password_hasher() -> MagicMock:
    hasher = MagicMock()
    hasher.hash.return_value = "hashed-password"
    return hasher


@pytest.fixture
def auth_service() -> MagicMock:
    auth = MagicMock()
    auth.validate_password_strength = MagicMock()
    return auth


@pytest.fixture
def service(user_repo, role_repo, password_hasher, auth_service) -> UserService:
    return UserService(user_repo, role_repo, password_hasher, auth_service)


def _create_dto(**overrides) -> CreateUserRequest:
    base = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "username": "ada",
        "temporary_password": "StrongPass1!",
        "role": UserRole.RESOURCE,
    }
    base.update(overrides)
    return CreateUserRequest(**base)


@pytest.mark.asyncio
async def test_create_user_rejects_weak_password(service, auth_service):
    auth_service.validate_password_strength.side_effect = WeakPasswordError("weak")
    with pytest.raises(WeakPasswordError):
        await service.create_user(_create_dto())


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_username(service, user_repo, auth_service):
    user_repo.find_by_username.return_value = SimpleNamespace(id=1)
    with pytest.raises(DuplicateUsernameError):
        await service.create_user(_create_dto())


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(service, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = SimpleNamespace(id=1)
    with pytest.raises(DuplicateEmailError):
        await service.create_user(_create_dto())


@pytest.mark.asyncio
async def test_create_user_rejects_unknown_role(service, user_repo, role_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = None
    role_repo.find_by_name.return_value = None
    with pytest.raises(ValidationError, match="Unknown role"):
        await service.create_user(_create_dto())


@pytest.mark.asyncio
async def test_create_user_happy_path(
    service, user_repo, role_repo, password_hasher
):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = None
    role_repo.find_by_name.return_value = SimpleNamespace(id=3)
    saved = SimpleNamespace(id=10, username="ada")
    user_repo.save.return_value = saved

    result = await service.create_user(_create_dto())

    assert result is saved
    password_hasher.hash.assert_called_once_with("StrongPass1!")
    user_repo.save.assert_awaited_once()
    saved_user = user_repo.save.await_args.args[0]
    assert saved_user.force_password_change is True
    assert saved_user.status == UserStatus.ACTIVE
    assert saved_user.role_id == 3


@pytest.mark.asyncio
async def test_list_users_aggregates_counts(service, user_repo):
    user_repo.list_users.return_value = [SimpleNamespace(id=1)]
    user_repo.count_all.return_value = 5
    user_repo.count_by_status.side_effect = [3, 2]

    result = await service.list_users(limit=10, offset=0)

    assert result.total == 5
    assert result.active_count == 3
    assert result.inactive_count == 2
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_get_user_not_found(service, user_repo):
    user_repo.find_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.get_user(99)


@pytest.mark.asyncio
async def test_lookup_user_by_id_and_username(service, user_repo):
    by_id = SimpleNamespace(id=5, username="bob")
    user_repo.find_by_id.return_value = by_id
    assert await service.lookup_user("5") is by_id

    user_repo.find_by_username.return_value = by_id
    assert await service.lookup_user("bob") is by_id

    user_repo.find_by_username.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.lookup_user("missing")


@pytest.mark.asyncio
async def test_deactivate_rejects_self(service):
    with pytest.raises(SelfOperationForbiddenError):
        await service.deactivate(1, acting_admin_id=1)


@pytest.mark.asyncio
async def test_deactivate_rejects_already_inactive(service, user_repo):
    user_repo.find_by_id.return_value = SimpleNamespace(
        id=2, status=UserStatus.INACTIVE
    )
    with pytest.raises(UserAlreadyInactiveError):
        await service.deactivate(2, acting_admin_id=1)


@pytest.mark.asyncio
async def test_deactivate_happy_path(service, user_repo):
    user = SimpleNamespace(id=2, status=UserStatus.ACTIVE)
    user_repo.find_by_id.return_value = user
    user_repo.save.return_value = user

    result = await service.deactivate(2, acting_admin_id=1)

    assert result.status == UserStatus.INACTIVE
    user_repo.save.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_reactivate_rejects_already_active(service, user_repo):
    user_repo.find_by_id.return_value = SimpleNamespace(
        id=2, status=UserStatus.ACTIVE
    )
    with pytest.raises(UserAlreadyActiveError):
        await service.reactivate(2, acting_admin_id=1)


@pytest.mark.asyncio
async def test_reactivate_happy_path(service, user_repo):
    user = SimpleNamespace(id=2, status=UserStatus.INACTIVE)
    user_repo.find_by_id.return_value = user
    user_repo.save.return_value = user

    result = await service.reactivate(2, acting_admin_id=1)

    assert result.status == UserStatus.ACTIVE
