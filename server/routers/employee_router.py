from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from server.core.dependencies import dependency_provider
from server.models.allocation import Allocation
from server.models.employee import Employee
from server.models.enums import EmployeeStatus, UserRole
from server.models.user import User
from server.schemas.requests.employee import AssignManagerRequest, UpdateEmployeeRequest
from server.schemas.requests.skill import AddSkillRequest
from server.schemas.response_values import EmployeeMessage
from server.schemas.responses.employee import (
    ActiveAllocationPreview,
    AssignManagerResponse,
    EmployeeActionResponse,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeSummaryResponse,
    EmployeeUpsertResponse,
)
from server.schemas.responses.skill import SkillListResponse, SkillResponse
from server.services.employee_service import EmployeeService
from server.services.skill_service import SkillService


class EmployeeRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/employees", tags=["employees"])
        self.router.add_api_route(
            "/by-user/{user_id}",
            self.update_employee,
            methods=["PUT"],
            response_model=EmployeeUpsertResponse,
        )
        self.router.add_api_route(
            "",
            self.list_employees,
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
            "/{employee_id}",
            self.get_employee,
            methods=["GET"],
            response_model=EmployeeDetailResponse,
        )
        self.router.add_api_route(
            "/{employee_id}/deactivate",
            self.deactivate_employee,
            methods=["POST"],
            response_model=EmployeeActionResponse,
        )
        self.router.add_api_route(
            "/{employee_id}/skills",
            self.list_skills,
            methods=["GET"],
            response_model=SkillListResponse,
        )
        self.router.add_api_route(
            "/{employee_id}/skills",
            self.add_skill,
            methods=["POST"],
            response_model=SkillResponse,
            status_code=status.HTTP_201_CREATED,
        )

    async def update_employee(
        self,
        user_id: int,
        body: UpdateEmployeeRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        employee_service: EmployeeService = Depends(dependency_provider.get_employee_service),
    ) -> EmployeeUpsertResponse | JSONResponse:
        result = await employee_service.update_employee(user_id, body)
        response = EmployeeUpsertResponse(
            id=result.employee.id,
            user_id=result.employee.user_id,
            status=EmployeeStatus(result.employee.status),
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

    async def list_employees(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        employee_service: EmployeeService = Depends(dependency_provider.get_employee_service),
        status_filter: EmployeeStatus | None = Query(default=None, alias="status"),
        department: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> EmployeeListResponse:
        result = await employee_service.list_employees(
            status=status_filter,
            department=department,
            limit=limit,
            offset=offset,
        )
        return EmployeeListResponse(
            items=[self._to_summary(employee) for employee in result.items],
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
        employee_service: EmployeeService = Depends(dependency_provider.get_employee_service),
    ) -> AssignManagerResponse:
        employee = await employee_service.assign_manager(body)
        return AssignManagerResponse(
            employee_id=employee.id,
            manager_id=employee.manager_id or 0,
            message=EmployeeMessage.MANAGER_ASSIGNED,
        )

    async def get_employee(
        self,
        employee_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        employee_service: EmployeeService = Depends(dependency_provider.get_employee_service),
    ) -> EmployeeDetailResponse:
        employee = await employee_service.get_employee(employee_id)
        allocations = await employee_service.get_active_allocations(employee_id)
        return self._to_detail(employee, allocations)

    async def deactivate_employee(
        self,
        employee_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        employee_service: EmployeeService = Depends(dependency_provider.get_employee_service),
    ) -> EmployeeActionResponse:
        await employee_service.deactivate_employee(employee_id)
        return EmployeeActionResponse(
            employee_id=employee_id,
            message=EmployeeMessage.EMPLOYEE_DEACTIVATED,
        )

    async def list_skills(
        self,
        employee_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> SkillListResponse:
        skills = await skill_service.list_skills(employee_id)
        return SkillListResponse(items=[self._to_skill(skill) for skill in skills])

    async def add_skill(
        self,
        employee_id: int,
        body: AddSkillRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> SkillResponse:
        skill = await skill_service.add_skill(employee_id, body)
        return self._to_skill(skill)

    def _to_summary(self, employee: Employee) -> EmployeeSummaryResponse:
        return EmployeeSummaryResponse(
            id=employee.id,
            full_name=employee.full_name,
            department=employee.department,
            status=EmployeeStatus(employee.status),
            is_active=employee.is_active,
        )

    def _to_detail(
        self, employee: Employee, allocations: list[Allocation]
    ) -> EmployeeDetailResponse:
        return EmployeeDetailResponse(
            id=employee.id,
            user_id=employee.user_id,
            full_name=employee.full_name,
            email=employee.email,
            department=employee.department,
            designation=employee.designation,
            status=EmployeeStatus(employee.status),
            is_active=employee.is_active,
            manager_id=employee.manager_id,
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
            skill_name=skill.skill_name,
            category=skill.category,
            proficiency_level=skill.proficiency_level,
        )
