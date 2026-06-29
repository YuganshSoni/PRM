from dataclasses import dataclass
from datetime import date

from server.core.user_role import user_role_enum
from server.core.exceptions import (
    DuplicateEmailError,
    EmployeeAlreadyActiveError,
    EmployeeAlreadyInactiveError,
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidUserRoleForEmployeeError,
    ManagerProfileNotFoundError,
    ManagerUserNotFoundError,
    ResourceStatusNotFoundError,
    SelfManagerAssignmentError,
    UserNotFoundError,
)
from server.models.resource import Resource
from server.models.enums import ResourceStatusEnum, UserRole
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.department_repository import DepartmentRepository
from server.repositories.designation_repository import DesignationRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.resource_status_repository import ResourceStatusRepository
from server.repositories.user_repository import UserRepository
from server.schemas.requests.resource import AssignManagerRequest, UpdateEmployeeRequest


@dataclass(frozen=True)
class EmployeeListResult:
    items: list[Resource]
    total: int
    bench_count: int
    allocated_count: int


@dataclass(frozen=True)
class EmployeeUpsertResult:
    resource: Resource
    created: bool


class EmployeeService:
    def __init__(
        self,
        resource_repository: ResourceRepository,
        user_repository: UserRepository,
        allocation_repository: AllocationRepository,
        department_repository: DepartmentRepository,
        designation_repository: DesignationRepository,
        resource_status_repository: ResourceStatusRepository,
    ) -> None:
        self._resource_repository = resource_repository
        self._user_repository = user_repository
        self._allocation_repository = allocation_repository
        self._department_repository = department_repository
        self._designation_repository = designation_repository
        self._resource_status_repository = resource_status_repository

    async def update_resource(
        self, user_id: int, dto: UpdateEmployeeRequest
    ) -> EmployeeUpsertResult:
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        if user_role_enum(user) not in (UserRole.RESOURCE, UserRole.MANAGER):
            raise InvalidUserRoleForEmployeeError(
                "User must have EMPLOYEE or MANAGER role"
            )

        email = str(dto.email)
        existing_email_user = await self._user_repository.find_by_email(email)
        if existing_email_user is not None and existing_email_user.id != user_id:
            raise DuplicateEmailError("Email already exists")

        user.full_name = dto.full_name
        user.email = email
        await self._user_repository.save(user)

        department = await self._department_repository.find_or_create_by_name(
            dto.department
        )
        designation = await self._designation_repository.find_or_create_by_name(
            dto.designation
        )

        existing = await self._resource_repository.find_by_user_id(user_id)
        if existing is None:
            bench_status = await self._resource_status_repository.find_by_name(
                ResourceStatusEnum.BENCH.value
            )
            if bench_status is None:
                raise ResourceStatusNotFoundError("Resource status BENCH not found")

            resource = Resource(
                user_id=user_id,
                department_id=department.id,
                designation_id=designation.id,
                resource_status_id=bench_status.id,
                is_active=True,
            )
            saved = await self._resource_repository.save(resource)
            loaded = await self._resource_repository.get_by_id_with_user(saved.id)
            return EmployeeUpsertResult(resource=loaded or saved, created=True)

        existing.department_id = department.id
        existing.designation_id = designation.id
        saved = await self._resource_repository.save(existing)
        loaded = await self._resource_repository.get_by_id_with_user(saved.id)
        return EmployeeUpsertResult(resource=loaded or saved, created=False)

    async def list_resources(
        self,
        *,
        status: ResourceStatusEnum | None,
        department: str | None,
        limit: int,
        offset: int,
    ) -> EmployeeListResult:
        items = await self._resource_repository.list_resources(
            status=status, department=department, limit=limit, offset=offset
        )
        total = await self._resource_repository.count_active_resources(
            status=status, department=department
        )
        bench_count = await self._resource_repository.count_by_status(
            ResourceStatusEnum.BENCH
        )
        allocated_count = await self._resource_repository.count_by_status(
            ResourceStatusEnum.ALLOCATED
        )
        return EmployeeListResult(
            items=items,
            total=total,
            bench_count=bench_count,
            allocated_count=allocated_count,
        )

    async def get_resource(self, resource_id: int) -> Resource:
        resource = await self._resource_repository.get_by_id_with_user(resource_id)
        if resource is None:
            raise EmployeeNotFoundError("Resource not found")
        return resource

    async def get_resource_by_user_id(self, user_id: int) -> Resource:
        resource = await self._resource_repository.find_by_user_id(user_id)
        if resource is None:
            raise EmployeeNotFoundError("Resource profile not found for user")
        loaded = await self._resource_repository.get_by_id_with_user(resource.id)
        return loaded if loaded is not None else resource

    async def get_active_allocations(self, resource_id: int):
        await self.get_resource(resource_id)
        return await self._allocation_repository.find_active_by_resource(resource_id)

    async def assign_manager(self, dto: AssignManagerRequest) -> Resource:
        if dto.resource_user_id == dto.manager_user_id:
            raise SelfManagerAssignmentError(
                "Resource and manager cannot be the same user"
            )

        resource = await self._resource_repository.find_by_user_id(
            dto.resource_user_id
        )
        if resource is None:
            raise EmployeeNotFoundError("Resource profile not found for user")

        manager_user = await self._user_repository.find_by_id(dto.manager_user_id)
        if manager_user is None:
            raise ManagerUserNotFoundError("Manager user not found")
        if user_role_enum(manager_user) != UserRole.MANAGER:
            raise InvalidManagerRoleError("Manager user must have MANAGER role")

        manager_resource = await self._resource_repository.find_by_user_id(
            dto.manager_user_id
        )
        if manager_resource is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an resource profile"
            )

        if resource.id == manager_resource.id:
            raise SelfManagerAssignmentError("Resource cannot be their own manager")

        resource.manager_id = manager_resource.id
        return await self._resource_repository.save(resource)

    async def deactivate_resource(self, resource_id: int) -> Resource:
        resource = await self.get_resource(resource_id)
        if not resource.is_active:
            raise EmployeeAlreadyInactiveError("Resource is already inactive")

        today = date.today()
        active_allocations = (
            await self._allocation_repository.find_active_by_resource(resource_id)
        )
        for allocation in active_allocations:
            allocation.to_date = today
            await self._allocation_repository.save(allocation)

        bench_status = await self._resource_status_repository.find_by_name(
            ResourceStatusEnum.BENCH.value
        )
        if bench_status is None:
            raise ResourceStatusNotFoundError("Resource status BENCH not found")

        resource.is_active = False
        resource.resource_status_id = bench_status.id
        await self._resource_repository.save(resource)

        return resource

    async def reactivate_resource(self, resource_id: int) -> Resource:
        resource = await self.get_resource(resource_id)
        if resource.is_active:
            raise EmployeeAlreadyActiveError("Resource is already active")

        bench_status = await self._resource_status_repository.find_by_name(
            ResourceStatusEnum.BENCH.value
        )
        if bench_status is None:
            raise ResourceStatusNotFoundError("Resource status BENCH not found")

        resource.is_active = True
        resource.resource_status_id = bench_status.id
        await self._resource_repository.save(resource)

        reloaded = await self._resource_repository.get_by_id_with_user(resource.id)
        return reloaded if reloaded is not None else resource
