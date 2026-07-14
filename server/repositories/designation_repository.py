from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.designation import Designation
from server.repositories.base_repository import BaseRepository


class DesignationRepository(BaseRepository[Designation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Designation)

    async def find_or_create_by_name(self, name: str) -> Designation:
        result = await self._session.execute(
            select(Designation).where(Designation.name == name)
        )
        designation = result.scalar_one_or_none()
        if designation is None:
            designation = Designation(name=name)
            designation = await self.add(designation)
        return designation
