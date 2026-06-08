"""find methods return None when not found; never catch DB exceptions."""

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, entity_id: int) -> T | None:
        return await self._session.get(self._model, entity_id)

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def list_all(self) -> list[T]:
        result = await self._session.execute(select(self._model))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(self._model)
        )
        return int(result.scalar_one())
