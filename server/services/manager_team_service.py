from server.core.exceptions import (
    EmployeeNotAllocatableError,
    EmployeeNotFoundError,
    ForbiddenError,
    ManagerProfileNotFoundError,
)
from server.models.enums import ResourceStatusEnum
from server.models.resource import Resource
from server.models.user import User
from server.repositories.resource_repository import ResourceRepository


class ManagerTeamService:
    """Scope manager-facing operations to employees assigned to that manager."""

    def __init__(self, resource_repository: ResourceRepository) -> None:
        self._resource_repository = resource_repository

    async def resolve_manager_resource_id(self, user: User) -> int:
        manager_resource = await self._resource_repository.find_by_user_id(user.id)
        if manager_resource is None:
            raise ManagerProfileNotFoundError("Manager profile not found")
        return manager_resource.id

    async def list_active_team_members(
        self, manager_resource_id: int, *, load_skills: bool = False
    ) -> list[Resource]:
        return await self._resource_repository.find_active_by_manager_id(
            manager_resource_id,
            load_skills=load_skills,
        )

    async def list_bench_team_members(
        self, manager_resource_id: int, *, load_skills: bool = False
    ) -> list[Resource]:
        return await self._resource_repository.find_by_manager_and_status(
            manager_resource_id,
            ResourceStatusEnum.BENCH,
            load_skills=load_skills,
        )

    async def get_team_member(
        self, manager_resource_id: int, resource_id: int
    ) -> Resource:
        resource = await self._resource_repository.get_by_id_with_user(resource_id)
        if resource is None:
            raise EmployeeNotFoundError("Resource not found")
        self.ensure_team_member(manager_resource_id, resource)
        return resource

    @staticmethod
    def ensure_team_member(manager_resource_id: int, resource: Resource) -> None:
        if not resource.is_active or resource.manager_id != manager_resource_id:
            raise EmployeeNotAllocatableError("Resource not in your team")

    @staticmethod
    def ensure_team_member_or_forbidden(
        manager_resource_id: int, resource: Resource
    ) -> None:
        if resource.manager_id != manager_resource_id:
            raise ForbiddenError("Resource not in your team")
