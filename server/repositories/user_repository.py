from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.enums import UserStatus
from server.models.user import User
from server.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def find_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def exists_by_username(self, username: str) -> bool:
        user = await self.find_by_username(username)
        return user is not None

    async def find_by_id(self, user_id: int) -> User | None:
        return await self.get_by_id(user_id)

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_users(self, limit: int, offset: int) -> list[User]:
        result = await self._session.execute(
            select(User).order_by(User.id).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one())

    async def count_by_status(self, status: UserStatus) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .where(User.status == status)
        )
        return int(result.scalar_one())

    async def save(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
