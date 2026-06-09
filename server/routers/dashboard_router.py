from typing import Annotated

from fastapi import APIRouter, Depends

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.responses.dashboard import (
    DashboardEmployeeDetailResponse,
    ResourceDashboardResponse,
)
from server.services.resource_dashboard_service import ResourceDashboardService


class DashboardRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/dashboard", tags=["dashboard"])
        self.router.add_api_route(
            "/resources",
            self.get_resource_dashboard,
            methods=["GET"],
            response_model=ResourceDashboardResponse,
        )
        self.router.add_api_route(
            "/employees/{employee_id}",
            self.get_employee_detail,
            methods=["GET"],
            response_model=DashboardEmployeeDetailResponse,
        )

    async def get_resource_dashboard(
        self,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        dashboard_service: ResourceDashboardService = Depends(
            dependency_provider.get_resource_dashboard_service
        ),
    ) -> ResourceDashboardResponse:
        return await dashboard_service.get_resource_dashboard(_manager)

    async def get_employee_detail(
        self,
        employee_id: int,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        dashboard_service: ResourceDashboardService = Depends(
            dependency_provider.get_resource_dashboard_service
        ),
    ) -> DashboardEmployeeDetailResponse:
        return await dashboard_service.get_employee_detail(employee_id, _manager)
