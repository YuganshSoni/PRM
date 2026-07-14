from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.resource_skill import ResourceSkill
from server.models.skill import Skill
from server.repositories.base_repository import BaseRepository


class SkillRepository(BaseRepository[ResourceSkill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ResourceSkill)

    async def find_by_resource_id(self, resource_id: int) -> list[ResourceSkill]:
        result = await self._session.execute(
            select(ResourceSkill)
            .where(ResourceSkill.resource_id == resource_id)
            .options(
                selectinload(ResourceSkill.skill).selectinload(Skill.category)
            )
            .order_by(ResourceSkill.id)
        )
        return list(result.scalars().unique().all())

    async def find_by_resource_and_name(
        self, resource_id: int, skill_name: str
    ) -> ResourceSkill | None:
        result = await self._session.execute(
            select(ResourceSkill)
            .join(ResourceSkill.skill)
            .where(
                ResourceSkill.resource_id == resource_id,
                Skill.name == skill_name,
            )
            .options(
                selectinload(ResourceSkill.skill).selectinload(Skill.category)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_resource_and_skill_id(
        self, resource_id: int, skill_id: int
    ) -> ResourceSkill | None:
        result = await self._session.execute(
            select(ResourceSkill).where(
                ResourceSkill.resource_id == resource_id,
                ResourceSkill.skill_id == skill_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, skill_id: int) -> ResourceSkill | None:
        result = await self._session.execute(
            select(ResourceSkill)
            .where(ResourceSkill.id == skill_id)
            .options(
                selectinload(ResourceSkill.skill).selectinload(Skill.category)
            )
        )
        return result.scalar_one_or_none()

    async def save(self, skill: ResourceSkill) -> ResourceSkill:
        return await self.add(skill)
