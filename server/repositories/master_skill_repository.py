from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.skill import Skill
from server.models.skill_category import SkillCategory
from server.repositories.base_repository import BaseRepository


class MasterSkillRepository(BaseRepository[Skill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Skill)

    async def find_by_name(self, name: str) -> Skill | None:
        result = await self._session.execute(
            select(Skill).where(Skill.name == name)
        )
        return result.scalar_one_or_none()

    async def find_by_name_insensitive(self, name: str) -> Skill | None:
        result = await self._session.execute(
            select(Skill).where(Skill.name.ilike(name.strip()))
        )
        return result.scalar_one_or_none()

    async def find_or_create(self, name: str, category_name: str) -> Skill:
        existing = await self.find_by_name(name)
        if existing is not None:
            return existing

        category_result = await self._session.execute(
            select(SkillCategory).where(SkillCategory.name == category_name)
        )
        category = category_result.scalar_one_or_none()
        if category is None:
            category = SkillCategory(name=category_name)
            self._session.add(category)
            await self._session.flush()

        skill = Skill(name=name, category_id=category.id)
        return await self.add(skill)
