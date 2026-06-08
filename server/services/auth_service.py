from dataclasses import dataclass

from server.core.exceptions import (
    AccountInactiveError,
    InvalidCredentialsError,
    PasswordMismatchError,
)
from server.core.jwt_token_service import JwtTokenService
from server.core.password_policy import PasswordPolicy
from server.core.security import PasswordHasher
from server.models.enums import UserStatus
from server.models.user import User
from server.repositories.user_repository import UserRepository

_INVALID_CREDENTIALS_MESSAGE = "Invalid username or password"


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    user: User


@dataclass(frozen=True)
class ChangePasswordResult:
    access_token: str
    user: User


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        jwt_token_service: JwtTokenService,
        password_policy: PasswordPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._jwt_token_service = jwt_token_service
        self._password_policy = password_policy

    async def login(self, username: str, password: str) -> LoginResult:
        user = await self._user_repository.find_by_username(username)
        if user is None:
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)
        if user.status == UserStatus.INACTIVE:
            raise AccountInactiveError("Account is inactive")
        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)

        token = self._jwt_token_service.create_access_token(user)
        return LoginResult(access_token=token, user=user)

    def validate_password_strength(self, password: str) -> None:
        self._password_policy.validate(password)

    async def change_password(
        self,
        user: User,
        new_password: str,
        confirm_password: str,
    ) -> ChangePasswordResult:
        if new_password != confirm_password:
            raise PasswordMismatchError("Passwords do not match")

        self.validate_password_strength(new_password)

        user.password_hash = self._password_hasher.hash(new_password)
        user.force_password_change = False
        await self._user_repository.save(user)

        token = self._jwt_token_service.create_access_token(user)
        return ChangePasswordResult(access_token=token, user=user)
