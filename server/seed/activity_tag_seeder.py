from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.activity_tag import ActivityTag
from server.seed.base_seeder import BaseSeeder

PREDEFINED_TAGS: list[tuple[int, str]] = [
    (1, "Backend API Development"),
    (2, "Microservices / Architecture"),
    (3, "Database Design & Queries"),
    (4, "WebSocket / Real-time Features"),
    (5, "Frontend Development"),
    (6, "Code Review / Mentoring"),
    (7, "Bug Fixing"),
    (8, "DevOps / Deployment"),
    (9, "Testing & QA"),
    (10, "Documentation"),
    (11, "Other"),
]


class ActivityTagSeeder(BaseSeeder):
    async def run(self, session: AsyncSession) -> None:
        result = await session.execute(select(ActivityTag))
        existing = {tag.name for tag in result.scalars().all()}

        for display_order, name in PREDEFINED_TAGS:
            if name in existing:
                continue
            session.add(
                ActivityTag(
                    name=name,
                    is_predefined=True,
                    display_order=display_order,
                )
            )

        await session.flush()
