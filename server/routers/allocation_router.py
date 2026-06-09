from typing import Annotated

from fastapi import APIRouter, Depends, Query

from server.core.dependencies import dependency_provider
from server.models.allocation import Allocation
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.responses.allocation import (
    AllocationListResponse,
    AllocationSummaryResponse,
)
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

    def _to_summary(self, allocation: Allocation) -> AllocationSummaryResponse:
        return AllocationSummaryResponse(
            id=allocation.id,
            employee_name=allocation.employee.full_name,
            project_name=allocation.project.name,
            utilisation_percent=allocation.utilisation_percent,
            from_date=allocation.from_date,
            to_date=allocation.to_date,
        )
