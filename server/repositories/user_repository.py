from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
