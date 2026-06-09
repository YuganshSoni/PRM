from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from server.core.dependencies import dependency_provider
from server.models.allocation import Allocation
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.allocation import CreateAllocationRequest
from server.schemas.response_values import AllocationMessage
from server.schemas.responses.allocation import (
    AllocationCreatedResponse,
    AllocationEndedResponse,
    AllocationListResponse,
    AllocationSummaryResponse,
    ProjectAllocationListResponse,
    ProjectAllocationSummaryResponse,
)
from server.services.allocation_service import AllocationService
from server.services.allocation_view_service import AllocationViewService


class AllocationRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/allocations", tags=["allocations"])
        self.router.add_api_route(
            "",
            self.list_allocations,
            methods=["GET"],
            response_model=AllocationListResponse,
        )
        self.router.add_api_route(
            "",
            self.create_allocation,
            methods=["POST"],
            response_model=AllocationCreatedResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "/by-project/{project_id}",
            self.list_project_allocations,
            methods=["GET"],
            response_model=ProjectAllocationListResponse,
        )
        self.router.add_api_route(
            "/{allocation_id}/end",
            self.end_allocation,
            methods=["POST"],
            response_model=AllocationEndedResponse,
        )

    async def list_allocations(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        allocation_view_service: AllocationViewService = Depends(
            dependency_provider.get_allocation_view_service
        ),
        employee_id: int | None = Query(default=None),
        project_id: int | None = Query(default=None),
        employee_name: str | None = Query(default=None),
        project_name: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> AllocationListResponse:
        result = await allocation_view_service.list_allocations(
            employee_id=employee_id,
            project_id=project_id,
            employee_name=employee_name,
            project_name=project_name,
            limit=limit,
            offset=offset,
        )
        return AllocationListResponse(
            items=[self._to_summary(allocation) for allocation in result.items],
            total=result.total,
            limit=limit,
            offset=offset,
        )

    async def create_allocation(
        self,
        body: CreateAllocationRequest,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        allocation_service: AllocationService = Depends(
            dependency_provider.get_allocation_service
        ),
    ) -> AllocationCreatedResponse:
        allocation = await allocation_service.create_allocation(body, _manager)
        return AllocationCreatedResponse(
            id=allocation.id,
            message=AllocationMessage.ALLOCATION_CREATED,
            employee_name=allocation.employee.full_name,
            project_name=allocation.project.name,
            utilisation_percent=allocation.utilisation_percent,
            from_date=allocation.from_date,
            to_date=allocation.to_date,
        )

    async def list_project_allocations(
        self,
        project_id: int,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        allocation_service: AllocationService = Depends(
            dependency_provider.get_allocation_service
        ),
    ) -> ProjectAllocationListResponse:
        project, allocations = await allocation_service.list_project_allocations(
            project_id, _manager
        )
        return ProjectAllocationListResponse(
            project_name=project.name,
            items=[
                ProjectAllocationSummaryResponse(
                    id=allocation.id,
                    employee_id=allocation.employee_id,
                    employee_name=allocation.employee.full_name,
                    utilisation_percent=allocation.utilisation_percent,
                    from_date=allocation.from_date,
                    to_date=allocation.to_date,
                )
                for allocation in allocations
            ],
        )

    async def end_allocation(
        self,
        allocation_id: int,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        allocation_service: AllocationService = Depends(
            dependency_provider.get_allocation_service
        ),
    ) -> AllocationEndedResponse:
        allocation = await allocation_service.end_allocation(allocation_id, _manager)
        return AllocationEndedResponse(
            message=AllocationMessage.ALLOCATION_ENDED,
            employee_name=allocation.employee.full_name,
            project_name=allocation.project.name,
            end_date=allocation.to_date,
        )

    def _to_summary(self, allocation: Allocation) -> AllocationSummaryResponse:
        return AllocationSummaryResponse(
            id=allocation.id,
            employee_name=allocation.employee.full_name,
            project_name=allocation.project.name,
            utilisation_percent=allocation.utilisation_percent,
            from_date=allocation.from_date,
            to_date=allocation.to_date,
        )
