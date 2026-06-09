from dataclasses import dataclass

from server.core.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    SelfOperationForbiddenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
)
from server.core.security import PasswordHasher
from server.models.enums import UserRole, UserStatus
from server.models.user import User
from server.repositories.user_repository import UserRepository
from server.schemas.requests.user import CreateUserRequest
from server.services.auth_service import AuthService


@dataclass(frozen=True)
class UserListResult:
    items: list[User]
    total: int
    active_count: int
    inactive_count: int


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        auth_service: AuthService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._auth_service = auth_service

    async def create_user(self, dto: CreateUserRequest) -> User:
        self._auth_service.validate_password_strength(dto.temporary_password)

        if await self._user_repository.find_by_username(dto.username):
            raise DuplicateUsernameError("Username already exists")
        if await self._user_repository.find_by_email(str(dto.email)):
            raise DuplicateEmailError("Email already exists")

        user = User(
            username=dto.username,
            email=str(dto.email),
            full_name=dto.full_name,
            password_hash=self._password_hasher.hash(dto.temporary_password),
            role=dto.role,
            status=UserStatus.ACTIVE,
            force_password_change=True,
        )
        return await self._user_repository.save(user)

    async def list_users(self, limit: int, offset: int) -> UserListResult:
        items = await self._user_repository.list_users(limit, offset)
        total = await self._user_repository.count_all()
        active_count = await self._user_repository.count_by_status(UserStatus.ACTIVE)
        inactive_count = await self._user_repository.count_by_status(UserStatus.INACTIVE)
        return UserListResult(
            items=items,
            total=total,
            active_count=active_count,
            inactive_count=inactive_count,
        )

    async def lookup_user(self, identifier: str) -> User:
        user = await self._resolve_identifier(identifier)
        if user is None:
            raise UserNotFoundError("User not found")
        return user

    async def get_user(self, user_id: int) -> User:
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return user

    async def reset_password(
        self,
        user_id: int,
        temporary_password: str,
        acting_admin_id: int,
    ) -> User:
        user = await self.get_user(user_id)
        self._auth_service.validate_password_strength(temporary_password)
        user.password_hash = self._password_hasher.hash(temporary_password)
        user.force_password_change = True
        return await self._user_repository.save(user)

    async def deactivate(self, user_id: int, acting_admin_id: int) -> User:
        self._guard_self_operation(user_id, acting_admin_id)
        user = await self.get_user(user_id)
        if user.status == UserStatus.INACTIVE:
            raise UserAlreadyInactiveError("User is already inactive")
        user.status = UserStatus.INACTIVE
        return await self._user_repository.save(user)

    async def reactivate(self, user_id: int, acting_admin_id: int) -> User:
        self._guard_self_operation(user_id, acting_admin_id)
        user = await self.get_user(user_id)
        if user.status == UserStatus.ACTIVE:
            raise UserAlreadyActiveError("User is already active")
        user.status = UserStatus.ACTIVE
        return await self._user_repository.save(user)

    async def _resolve_identifier(self, identifier: str) -> User | None:
        stripped = identifier.strip()
        if stripped.isdigit():
            return await self._user_repository.find_by_id(int(stripped))
        return await self._user_repository.find_by_username(stripped)

    def _guard_self_operation(self, user_id: int, acting_admin_id: int) -> None:
        if user_id == acting_admin_id:
            raise SelfOperationForbiddenError(
                "You cannot deactivate or reactivate your own account"
            )
