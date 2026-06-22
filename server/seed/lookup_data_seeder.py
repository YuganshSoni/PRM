from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.role import Role
from server.models.resource_status import ResourceStatus
from server.models.skill_category import SkillCategory
from server.seed.base_seeder import BaseSeeder

PREDEFINED_ROLES = ["ADMIN", "MANAGER", "RESOURCE"]
PREDEFINED_RESOURCE_STATUSES = ["BENCH", "ALLOCATED"]
PREDEFINED_SKILL_CATEGORIES = ["BACKEND", "FRONTEND", "DEVOPS", "QA", "OTHER"]

class LookupDataSeeder(BaseSeeder):
    async def run(self, session: AsyncSession) -> None:
        # Seed Roles
        result = await session.execute(select(Role))
        existing_roles = {r.name for r in result.scalars().all()}
        for name in PREDEFINED_ROLES:
            if name not in existing_roles:
                session.add(Role(name=name))

        # Seed Resource Statuses
        result = await session.execute(select(ResourceStatus))
        existing_statuses = {s.name for s in result.scalars().all()}
        for name in PREDEFINED_RESOURCE_STATUSES:
            if name not in existing_statuses:
                session.add(ResourceStatus(name=name))

        # Seed Skill Categories
        result = await session.execute(select(SkillCategory))
        existing_categories = {c.name for c in result.scalars().all()}
        for name in PREDEFINED_SKILL_CATEGORIES:
            if name not in existing_categories:
                session.add(SkillCategory(name=name))

        await session.flush()
