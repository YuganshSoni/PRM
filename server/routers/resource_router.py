from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from server.core.dependencies import dependency_provider
from server.models.allocation import Allocation
from server.models.resource import Resource
from server.models.enums import ResourceStatusEnum, UserRole, UserStatus
from server.models.user import User
from server.schemas.requests.resource import AssignManagerRequest, UpdateEmployeeRequest
from server.schemas.requests.skill import AddSkillRequest
from server.schemas.response_values import EmployeeMessage
from server.schemas.responses.resource import (
    ActiveAllocationPreview,
    AssignManagerResponse,
    EmployeeActionResponse,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeSummaryResponse,
    EmployeeUpsertResponse,
)
from server.schemas.responses.skill import SkillListResponse, SkillResponse
from server.services.resource_mapper import ResourceMapper
from server.services.resource_service import EmployeeService
from server.services.skill_service import SkillService


class EmployeeRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/resources", tags=["resources"])
        self.router.add_api_route(
            "/by-user/{user_id}",
            self.get_resource_by_user,
            methods=["GET"],
            response_model=EmployeeDetailResponse,
        )
        self.router.add_api_route(
            "/by-user/{user_id}",
            self.update_resource,
            methods=["PUT"],
            response_model=EmployeeUpsertResponse,
        )
        self.router.add_api_route(
            "",
            self.list_resources,
            methods=["GET"],
            response_model=EmployeeListResponse,
        )
        self.router.add_api_route(
            "/assign-manager",
            self.assign_manager,
            methods=["PUT"],
            response_model=AssignManagerResponse,
        )
        self.router.add_api_route(
            "/{resource_id}",
            self.get_resource,
            methods=["GET"],
            response_model=EmployeeDetailResponse,
        )
        self.router.add_api_route(
            "/{resource_id}/deactivate",
            self.deactivate_resource,
            methods=["POST"],
            response_model=EmployeeActionResponse,
        )
        self.router.add_api_route(
            "/{resource_id}/reactivate",
            self.reactivate_resource,
            methods=["POST"],
            response_model=EmployeeActionResponse,
        )
        self.router.add_api_route(
            "/{resource_id}/skills",
            self.list_skills,
            methods=["GET"],
            response_model=SkillListResponse,
        )
        self.router.add_api_route(
            "/{resource_id}/skills",
            self.add_skill,
            methods=["POST"],
            response_model=SkillResponse,
            status_code=status.HTTP_201_CREATED,
        )

    async def update_resource(
        self,
        user_id: int,
        body: UpdateEmployeeRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> EmployeeUpsertResponse | JSONResponse:
        result = await resource_service.update_resource(user_id, body)
        response = EmployeeUpsertResponse(
            id=result.resource.id,
            user_id=result.resource.user_id,
            status=ResourceMapper.status(result.resource),
            message=(
                EmployeeMessage.PROFILE_CREATED
                if result.created
                else EmployeeMessage.PROFILE_UPDATED
            ),
            created=result.created,
        )
        if result.created:
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=response.model_dump(),
            )
        return response

    async def list_resources(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
        status_filter: ResourceStatusEnum | None = Query(default=None, alias="status"),
        department: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> EmployeeListResponse:
        result = await resource_service.list_resources(
            status=status_filter,
            department=department,
            limit=limit,
            offset=offset,
        )
        return EmployeeListResponse(
            items=[self._to_summary(resource) for resource in result.items],
            total=result.total,
            bench_count=result.bench_count,
            allocated_count=result.allocated_count,
            limit=limit,
            offset=offset,
        )

    async def assign_manager(
        self,
        body: AssignManagerRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> AssignManagerResponse:
        resource = await resource_service.assign_manager(body)
        return AssignManagerResponse(
            resource_id=resource.id,
            manager_id=resource.manager_id or 0,
            message=EmployeeMessage.MANAGER_ASSIGNED,
        )

    async def get_resource(
        self,
        resource_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> EmployeeDetailResponse:
        resource = await resource_service.get_resource(resource_id)
        allocations = await resource_service.get_active_allocations(resource_id)
        return self._to_detail(resource, allocations)

    async def get_resource_by_user(
        self,
        user_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> EmployeeDetailResponse:
        resource = await resource_service.get_resource_by_user_id(user_id)
        allocations = await resource_service.get_active_allocations(resource.id)
        return self._to_detail(resource, allocations)

    async def deactivate_resource(
        self,
        resource_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> EmployeeActionResponse:
        await resource_service.deactivate_resource(resource_id)
        return EmployeeActionResponse(
            resource_id=resource_id,
            message=EmployeeMessage.EMPLOYEE_DEACTIVATED,
        )

    async def reactivate_resource(
        self,
        resource_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        resource_service: EmployeeService = Depends(dependency_provider.get_resource_service),
    ) -> EmployeeActionResponse:
        resource = await resource_service.reactivate_resource(resource_id)
        message = EmployeeMessage.EMPLOYEE_REACTIVATED
        if (
            resource.user is not None
            and resource.user.status == UserStatus.INACTIVE
        ):
            message = EmployeeMessage.EMPLOYEE_REACTIVATED_LOGIN_BLOCKED
        return EmployeeActionResponse(
            resource_id=resource.id,
            message=message,
        )

    async def list_skills(
        self,
        resource_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> SkillListResponse:
        skills = await skill_service.list_skills(resource_id)
        return SkillListResponse(items=[self._to_skill(skill) for skill in skills])

    async def add_skill(
        self,
        resource_id: int,
        body: AddSkillRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> SkillResponse:
        skill = await skill_service.add_skill(resource_id, body)
        return self._to_skill(skill)

    def _to_summary(self, resource: Resource) -> EmployeeSummaryResponse:
        return EmployeeSummaryResponse(
            id=resource.id,
            full_name=ResourceMapper.full_name(resource),
            department=ResourceMapper.department_name(resource),
            status=ResourceMapper.status(resource),
            is_active=resource.is_active,
        )

    def _to_detail(
        self, resource: Resource, allocations: list[Allocation]
    ) -> EmployeeDetailResponse:
        return EmployeeDetailResponse(
            id=resource.id,
            user_id=resource.user_id,
            full_name=ResourceMapper.full_name(resource),
            email=ResourceMapper.email(resource),
            department=ResourceMapper.department_name(resource),
            designation=ResourceMapper.designation_name(resource),
            status=ResourceMapper.status(resource),
            is_active=resource.is_active,
            manager_id=resource.manager_id,
            active_allocations=[
                ActiveAllocationPreview(
                    project_name=allocation.project.name,
                    utilisation_percent=allocation.utilisation_percent,
                    to_date=allocation.to_date,
                )
                for allocation in allocations
            ],
        )

    def _to_skill(self, skill) -> SkillResponse:
        return SkillResponse(
            id=skill.id,
            skill_name=ResourceMapper.skill_name(skill),
            category=ResourceMapper.skill_category(skill),
            proficiency_level=skill.proficiency_level,
        )
