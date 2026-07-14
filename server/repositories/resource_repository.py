from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.department import Department
from server.models.resource import Resource
from server.models.resource_status import ResourceStatus
from server.models.user import User
from server.models.enums import ResourceStatusEnum
from server.repositories.base_repository import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Resource)

    def _list_options(self):
        from server.models.resource_skill import ResourceSkill
        from server.models.skill import Skill

        return (
            selectinload(Resource.user),
            selectinload(Resource.department),
            selectinload(Resource.designation),
            selectinload(Resource.resource_status),
            selectinload(Resource.skills).selectinload(ResourceSkill.skill).selectinload(
                Skill.category
            ),
        )

    async def get_by_id_with_user(self, resource_id: int) -> Resource | None:
        result = await self._session.execute(
            select(Resource)
            .options(
                selectinload(Resource.user).selectinload(User.role),
                selectinload(Resource.department),
                selectinload(Resource.designation),
                selectinload(Resource.resource_status),
            )
            .where(Resource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def find_by_user_id(self, user_id: int) -> Resource | None:
        result = await self._session.execute(
            select(Resource).where(Resource.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Resource]:
        result = await self._session.execute(
            select(Resource)
            .where(Resource.is_active.is_(True))
            .options(*self._list_options())
            .order_by(Resource.id)
        )
        return list(result.scalars().unique().all())

    async def list_resources(
        self,
        *,
        status: ResourceStatusEnum | None,
        department: str | None,
        limit: int,
        offset: int,
    ) -> list[Resource]:
        query = (
            select(Resource)
            .where(Resource.is_active.is_(True))
            .options(*self._list_options())
        )
        if status is not None:
            query = query.join(Resource.resource_status).where(
                ResourceStatus.name == status.value
            )
        if department is not None:
            query = query.join(Resource.department).where(
                Department.name == department
            )
        query = query.order_by(Resource.id).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def count_active_resources(
        self,
        *,
        status: ResourceStatusEnum | None = None,
        department: str | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Resource)
            .where(Resource.is_active.is_(True))
        )
        if status is not None:
            query = query.join(Resource.resource_status).where(
                ResourceStatus.name == status.value
            )
        if department is not None:
            query = query.join(Resource.department).where(
                Department.name == department
            )
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def count_by_status(self, status: ResourceStatusEnum) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Resource)
            .join(Resource.resource_status)
            .where(
                Resource.is_active.is_(True),
                ResourceStatus.name == status.value,
            )
        )
        return int(result.scalar_one())

    async def find_by_manager_and_status(
        self,
        manager_resource_id: int,
        status: ResourceStatusEnum,
        *,
        load_skills: bool = False,
    ) -> list[Resource]:
        query = (
            select(Resource)
            .join(Resource.resource_status)
            .where(
                Resource.manager_id == manager_resource_id,
                ResourceStatus.name == status.value,
                Resource.is_active.is_(True),
            )
            .order_by(Resource.id)
        )
        options = [
            selectinload(Resource.user),
            selectinload(Resource.department),
            selectinload(Resource.resource_status),
        ]
        if load_skills:
            from server.models.resource_skill import ResourceSkill
            from server.models.skill import Skill

            options.append(
                selectinload(Resource.skills)
                .selectinload(ResourceSkill.skill)
                .selectinload(Skill.category)
            )
        query = query.options(*options)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def find_active_by_manager_id(
        self,
        manager_resource_id: int,
        *,
        load_skills: bool = False,
    ) -> list[Resource]:
        from server.models.resource_skill import ResourceSkill
        from server.models.skill import Skill

        options = [
            selectinload(Resource.user),
            selectinload(Resource.resource_status),
        ]
        if load_skills:
            options.append(
                selectinload(Resource.skills)
                .selectinload(ResourceSkill.skill)
                .selectinload(Skill.category)
            )
        else:
            options.append(
                selectinload(Resource.skills).selectinload(ResourceSkill.skill)
            )

        result = await self._session.execute(
            select(Resource)
            .where(
                Resource.manager_id == manager_resource_id,
                Resource.is_active.is_(True),
            )
            .options(*options)
            .order_by(Resource.id)
        )
        return list(result.scalars().unique().all())

    async def count_by_manager_and_status(
        self,
        manager_resource_id: int,
        status: ResourceStatusEnum,
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Resource)
            .join(Resource.resource_status)
            .where(
                Resource.manager_id == manager_resource_id,
                ResourceStatus.name == status.value,
                Resource.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def save(self, resource: Resource) -> Resource:
        return await self.add(resource)
