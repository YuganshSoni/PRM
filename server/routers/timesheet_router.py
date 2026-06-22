from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.timesheet import SubmitTimesheetRequest
from server.schemas.response_values import TimesheetMessage
from server.schemas.responses.timesheet import (
    MissedReminderResponse,
    TeamTimesheetListResponse,
    TimesheetDetailResponse,
    TimesheetListResponse,
    TimesheetSubmittedResponse,
)
from server.schemas.responses.timesheet_compliance import (
    ComplianceRestoreResponse,
    TeamComplianceListResponse,
)
from server.services.timesheet_compliance_service import TimesheetComplianceService
from server.services.timesheet_service import TimesheetService


class TimesheetRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/timesheets", tags=["timesheets"])
        self.router.add_api_route(
            "",
            self.submit_timesheet,
            methods=["POST"],
            response_model=TimesheetSubmittedResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "/mine",
            self.list_my_timesheets,
            methods=["GET"],
            response_model=TimesheetListResponse,
        )
        self.router.add_api_route(
            "/mine/missed-reminder",
            self.get_missed_reminder,
            methods=["GET"],
            response_model=MissedReminderResponse,
        )
        self.router.add_api_route(
            "/team",
            self.list_team_timesheets,
            methods=["GET"],
            response_model=TeamTimesheetListResponse,
        )
        self.router.add_api_route(
            "/compliance/team",
            self.list_team_compliance,
            methods=["GET"],
            response_model=TeamComplianceListResponse,
        )
        self.router.add_api_route(
            "/compliance/{resource_id}/restore",
            self.restore_compliance,
            methods=["POST"],
            response_model=ComplianceRestoreResponse,
        )
        self.router.add_api_route(
            "/{timesheet_id}",
            self.get_timesheet_detail,
            methods=["GET"],
            response_model=TimesheetDetailResponse,
        )

    async def submit_timesheet(
        self,
        body: SubmitTimesheetRequest,
        _resource: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.RESOURCE))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        timesheet_service: TimesheetService = Depends(
            dependency_provider.get_timesheet_service
        ),
    ) -> TimesheetSubmittedResponse:
        timesheet = await timesheet_service.submit_timesheet(body, _resource)
        return TimesheetSubmittedResponse(
            id=timesheet.id,
            message=TimesheetMessage.TIMESHEET_SUBMITTED,
            week_start=timesheet.week_start,
            total_hours=timesheet.total_hours,
            status=timesheet.status,
        )

    async def list_my_timesheets(
        self,
        _resource: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.RESOURCE))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        timesheet_service: TimesheetService = Depends(
            dependency_provider.get_timesheet_service
        ),
    ) -> TimesheetListResponse:
        items = await timesheet_service.list_my_timesheets(_resource)
        return TimesheetListResponse(items=items)

    async def get_missed_reminder(
        self,
        _resource: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.RESOURCE))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        timesheet_service: TimesheetService = Depends(
            dependency_provider.get_timesheet_service
        ),
    ) -> MissedReminderResponse:
        return await timesheet_service.get_missed_reminder(_resource)

    async def list_team_timesheets(
        self,
        week_start: Annotated[date, Query()],
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        timesheet_service: TimesheetService = Depends(
            dependency_provider.get_timesheet_service
        ),
    ) -> TeamTimesheetListResponse:
        return await timesheet_service.list_team_timesheets(_manager, week_start)

    async def list_team_compliance(
        self,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        compliance_service: TimesheetComplianceService = Depends(
            dependency_provider.get_timesheet_compliance_service
        ),
    ) -> TeamComplianceListResponse:
        items = await compliance_service.list_team_compliance_rows(_manager)
        return TeamComplianceListResponse(items=items)

    async def restore_compliance(
        self,
        resource_id: int,
        week_start: Annotated[date, Query()],
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        compliance_service: TimesheetComplianceService = Depends(
            dependency_provider.get_timesheet_compliance_service
        ),
    ) -> ComplianceRestoreResponse:
        record = await compliance_service.restore_access(
            _manager, resource_id, week_start
        )
        return ComplianceRestoreResponse(
            resource_id=record.resource_id,
            week_start=record.week_start,
            status=record.status,
            message="Timesheet submission access restored.",
        )

    async def get_timesheet_detail(
        self,
        timesheet_id: int,
        user: Annotated[
            User,
            Depends(
                dependency_provider.require_role(
                    UserRole.MANAGER, UserRole.RESOURCE
                )
            ),
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        timesheet_service: TimesheetService = Depends(
            dependency_provider.get_timesheet_service
        ),
    ) -> TimesheetDetailResponse:
        return await timesheet_service.get_timesheet_detail(timesheet_id, user)
