from typing import Any

import httpx

from client.config import ClientSettings
from client.exceptions import ApiRequestError, NetworkError, SessionNotAuthenticatedError
from client.schemas.auth import (
    ChangePasswordResponse,
    CurrentUserResponse,
    ErrorBody,
    LoginResponse,
    LogoutResponse,
)
from client.schemas.resource import (
    AssignManagerResponse,
    EmployeeActionResponse,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeUpsertResponse,
)
from client.schemas.activity_tag import ActivityTagListResponse
from client.schemas.allocation import (
    AllocationCreatedResponse,
    AllocationEndedResponse,
    AllocationListResponse,
    MyAllocationListResponse,
    ProjectAllocationListResponse,
    WeekAllocationContextResponse,
)
from client.schemas.timesheet import (
    MissedReminderResponse,
    TeamTimesheetListResponse,
    TimesheetDetailResponse,
    TimesheetListResponse,
    TimesheetSubmittedResponse,
)
from client.schemas.config import SystemConfigResponse, SystemConfigUpdatedResponse
from client.schemas.dashboard import (
    DashboardEmployeeDetailResponse,
    ResourceDashboardResponse,
)
from client.schemas.milestone import (
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneUpdatedResponse,
)
from client.schemas.project import (
    ManagedProjectListResponse,
    ManagerProjectDetailResponse,
    ProjectCreatedResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectUpdatedResponse,
)
from client.schemas.skill import SkillListResponse, SkillResponse
from client.schemas.user import (
    UserActionResponse,
    UserCreatedResponse,
    UserListResponse,
    UserSummaryResponse,
)
from client.schemas.ai import RiskSummaryResponse, SkillMatchResponse
from client.schemas.allocation import BulkAllocationCreatedResponse, BulkCreateAllocationRequest
from client.schemas.team_build import TeamBuildResponse
from client.session import Session, SessionManager
from server.models.enums import UserRole


class HttpxClient:
    def __init__(
        self,
        settings: ClientSettings,
        session_manager: SessionManager,
    ) -> None:
        self._settings = settings
        self._session_manager = session_manager

    async def login(self, username: str, password: str) -> LoginResponse:
        response = await self._request(
            "POST",
            "/auth/login",
            json={"username": username, "password": password},
            authenticated=False,
        )
        body = LoginResponse.model_validate(response.json())
        self._session_manager.set_session(
            Session(
                access_token=body.access_token,
                role=UserRole(body.role),
                force_password_change=body.force_password_change,
                full_name=body.full_name,
            )
        )
        return body

    async def change_password(
        self, new_password: str, confirm_password: str
    ) -> ChangePasswordResponse:
        response = await self._request(
            "POST",
            "/auth/change-password",
            json={
                "new_password": new_password,
                "confirm_password": confirm_password,
            },
            authenticated=True,
        )
        body = ChangePasswordResponse.model_validate(response.json())
        session = self._session_manager.current
        if session is not None:
            self._session_manager.set_session(
                Session(
                    access_token=body.access_token,
                    role=UserRole(body.role),
                    force_password_change=body.force_password_change,
                    full_name=session.full_name,
                )
            )
        return body

    async def logout(self) -> LogoutResponse:
        response = await self._request(
            "POST",
            "/auth/logout",
            authenticated=True,
        )
        return LogoutResponse.model_validate(response.json())

    async def me(self) -> CurrentUserResponse:
        response = await self._request("GET", "/auth/me", authenticated=True)
        return CurrentUserResponse.model_validate(response.json())

    async def create_user(
        self,
        full_name: str,
        email: str,
        username: str,
        temporary_password: str,
        role: str,
    ) -> UserCreatedResponse:
        response = await self._request(
            "POST",
            "/users",
            json={
                "full_name": full_name,
                "email": email,
                "username": username,
                "temporary_password": temporary_password,
                "role": role,
            },
            authenticated=True,
        )
        return UserCreatedResponse.model_validate(response.json())

    async def list_users(
        self, limit: int = 50, offset: int = 0
    ) -> UserListResponse:
        response = await self._request(
            "GET",
            "/users",
            params={"limit": str(limit), "offset": str(offset)},
            authenticated=True,
        )
        return UserListResponse.model_validate(response.json())

    async def lookup_user(self, identifier: str) -> UserSummaryResponse:
        response = await self._request(
            "GET",
            "/users/lookup",
            params={"identifier": identifier},
            authenticated=True,
        )
        return UserSummaryResponse.model_validate(response.json())

    async def reset_password(
        self, user_id: int, temporary_password: str
    ) -> UserActionResponse:
        response = await self._request(
            "POST",
            f"/users/{user_id}/reset-password",
            json={"temporary_password": temporary_password},
            authenticated=True,
        )
        return UserActionResponse.model_validate(response.json())

    async def deactivate_user(self, user_id: int) -> UserActionResponse:
        response = await self._request(
            "POST",
            f"/users/{user_id}/deactivate",
            authenticated=True,
        )
        return UserActionResponse.model_validate(response.json())

    async def reactivate_user(self, user_id: int) -> UserActionResponse:
        response = await self._request(
            "POST",
            f"/users/{user_id}/reactivate",
            authenticated=True,
        )
        return UserActionResponse.model_validate(response.json())

    async def update_employee_by_user(
        self,
        user_id: int,
        full_name: str,
        email: str,
        department: str,
        designation: str,
    ) -> EmployeeUpsertResponse:
        response = await self._request(
            "PUT",
            f"/resources/by-user/{user_id}",
            json={
                "full_name": full_name,
                "email": email,
                "department": department,
                "designation": designation,
            },
            authenticated=True,
        )
        return EmployeeUpsertResponse.model_validate(response.json())

    async def list_employees(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EmployeeListResponse:
        params: dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
        }
        if status:
            params["status"] = status
        if department:
            params["department"] = department
        response = await self._request(
            "GET",
            "/resources",
            params=params,
            authenticated=True,
        )
        return EmployeeListResponse.model_validate(response.json())

    async def get_employee(self, employee_id: int) -> EmployeeDetailResponse:
        response = await self._request(
            "GET",
            f"/resources/{employee_id}",
            authenticated=True,
        )
        return EmployeeDetailResponse.model_validate(response.json())

    async def deactivate_employee(self, employee_id: int) -> EmployeeActionResponse:
        response = await self._request(
            "POST",
            f"/resources/{employee_id}/deactivate",
            authenticated=True,
        )
        return EmployeeActionResponse.model_validate(response.json())

    async def assign_manager(
        self, employee_user_id: int, manager_user_id: int
    ) -> AssignManagerResponse:
        response = await self._request(
            "PUT",
            "/resources/assign-manager",
            json={
                "resource_user_id": employee_user_id,
                "manager_user_id": manager_user_id,
            },
            authenticated=True,
        )
        return AssignManagerResponse.model_validate(response.json())

    async def list_employee_skills(self, employee_id: int) -> SkillListResponse:
        response = await self._request(
            "GET",
            f"/resources/{employee_id}/skills",
            authenticated=True,
        )
        return SkillListResponse.model_validate(response.json())

    async def add_skill(
        self,
        employee_id: int,
        skill_name: str,
        category: str,
        proficiency_level: str,
    ) -> SkillResponse:
        response = await self._request(
            "POST",
            f"/resources/{employee_id}/skills",
            json={
                "skill_name": skill_name,
                "category": category,
                "proficiency_level": proficiency_level,
            },
            authenticated=True,
        )
        return SkillResponse.model_validate(response.json())

    async def update_skill_proficiency(
        self, skill_id: int, proficiency_level: str
    ) -> None:
        await self._request(
            "PUT",
            f"/skills/{skill_id}",
            json={"proficiency_level": proficiency_level},
            authenticated=True,
        )

    async def remove_skill(self, skill_id: int) -> None:
        await self._request(
            "DELETE",
            f"/skills/{skill_id}",
            authenticated=True,
        )

    async def create_project(
        self,
        *,
        name: str,
        description: str | None,
        start_date: str,
        end_date: str,
        status: str,
        manager_id: int,
        total_story_points: int,
    ) -> ProjectCreatedResponse:
        response = await self._request(
            "POST",
            "/projects",
            json={
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "manager_id": manager_id,
                "total_story_points": total_story_points,
            },
            authenticated=True,
        )
        return ProjectCreatedResponse.model_validate(response.json())

    async def list_projects(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectListResponse:
        params: dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
        }
        if status:
            params["status"] = status
        response = await self._request(
            "GET",
            "/projects",
            params=params,
            authenticated=True,
        )
        return ProjectListResponse.model_validate(response.json())

    async def get_project(self, project_id: int) -> ProjectDetailResponse:
        response = await self._request(
            "GET",
            f"/projects/{project_id}",
            authenticated=True,
        )
        return ProjectDetailResponse.model_validate(response.json())

    async def update_project(
        self,
        project_id: int,
        *,
        name: str,
        description: str | None,
        start_date: str,
        end_date: str,
        status: str,
        manager_id: int,
        total_story_points: int,
    ) -> ProjectUpdatedResponse:
        response = await self._request(
            "PUT",
            f"/projects/{project_id}",
            json={
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "manager_id": manager_id,
                "total_story_points": total_story_points,
            },
            authenticated=True,
        )
        return ProjectUpdatedResponse.model_validate(response.json())

    async def list_project_milestones(
        self, project_id: int
    ) -> MilestoneListResponse:
        response = await self._request(
            "GET",
            f"/projects/{project_id}/milestones",
            authenticated=True,
        )
        return MilestoneListResponse.model_validate(response.json())

    async def add_milestone(
        self,
        project_id: int,
        *,
        title: str,
        due_date: str,
        story_points: int,
    ) -> MilestoneResponse:
        response = await self._request(
            "POST",
            f"/projects/{project_id}/milestones",
            json={
                "title": title,
                "due_date": due_date,
                "story_points": story_points,
            },
            authenticated=True,
        )
        return MilestoneResponse.model_validate(response.json())

    async def update_milestone_status(
        self, milestone_id: int, status: str
    ) -> MilestoneUpdatedResponse:
        response = await self._request(
            "PUT",
            f"/milestones/{milestone_id}",
            json={"status": status},
            authenticated=True,
        )
        return MilestoneUpdatedResponse.model_validate(response.json())

    async def get_config(self) -> SystemConfigResponse:
        response = await self._request("GET", "/config", authenticated=True)
        return SystemConfigResponse.model_validate(response.json())

    async def update_config(self, **fields: str | int) -> SystemConfigUpdatedResponse:
        response = await self._request(
            "PUT",
            "/config",
            json=fields,
            authenticated=True,
        )
        return SystemConfigUpdatedResponse.model_validate(response.json())

    async def list_allocations(
        self,
        *,
        employee_id: int | None = None,
        project_id: int | None = None,
        employee_name: str | None = None,
        project_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AllocationListResponse:
        params: dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
        }
        if employee_id is not None:
            params["employee_id"] = str(employee_id)
        if project_id is not None:
            params["project_id"] = str(project_id)
        if employee_name:
            params["employee_name"] = employee_name
        if project_name:
            params["project_name"] = project_name
        response = await self._request(
            "GET",
            "/allocations",
            params=params,
            authenticated=True,
        )
        return AllocationListResponse.model_validate(response.json())

    async def get_resource_dashboard(self) -> ResourceDashboardResponse:
        response = await self._request(
            "GET",
            "/dashboard/resources",
            authenticated=True,
        )
        return ResourceDashboardResponse.model_validate(response.json())

    async def create_allocation(
        self,
        *,
        employee_id: int,
        project_id: int,
        utilisation_percent: int,
        from_date: str,
        to_date: str,
    ) -> AllocationCreatedResponse:
        response = await self._request(
            "POST",
            "/allocations",
            json={
                "resource_id": employee_id,
                "project_id": project_id,
                "utilisation_percent": utilisation_percent,
                "from_date": from_date,
                "to_date": to_date,
            },
            authenticated=True,
        )
        return AllocationCreatedResponse.model_validate(response.json())

    async def end_allocation(self, allocation_id: int) -> AllocationEndedResponse:
        response = await self._request(
            "POST",
            f"/allocations/{allocation_id}/end",
            authenticated=True,
        )
        return AllocationEndedResponse.model_validate(response.json())

    async def list_project_allocations(
        self, project_id: int
    ) -> ProjectAllocationListResponse:
        response = await self._request(
            "GET",
            f"/allocations/by-project/{project_id}",
            authenticated=True,
        )
        return ProjectAllocationListResponse.model_validate(response.json())

    async def list_managed_projects(self) -> ManagedProjectListResponse:
        response = await self._request(
            "GET",
            "/projects/mine",
            authenticated=True,
        )
        return ManagedProjectListResponse.model_validate(response.json())

    async def get_manager_project_detail(
        self, project_id: int
    ) -> ManagerProjectDetailResponse:
        response = await self._request(
            "GET",
            f"/projects/mine/{project_id}",
            authenticated=True,
        )
        return ManagerProjectDetailResponse.model_validate(response.json())

    async def get_missed_reminder(self) -> MissedReminderResponse:
        response = await self._request(
            "GET",
            "/timesheets/mine/missed-reminder",
            authenticated=True,
        )
        return MissedReminderResponse.model_validate(response.json())

    async def list_my_timesheets(self) -> TimesheetListResponse:
        response = await self._request(
            "GET",
            "/timesheets/mine",
            authenticated=True,
        )
        return TimesheetListResponse.model_validate(response.json())

    async def list_team_timesheets(
        self, *, week_start: str
    ) -> TeamTimesheetListResponse:
        response = await self._request(
            "GET",
            "/timesheets/team",
            params={"week_start": week_start},
            authenticated=True,
        )
        return TeamTimesheetListResponse.model_validate(response.json())

    async def get_timesheet_detail(self, timesheet_id: int) -> TimesheetDetailResponse:
        response = await self._request(
            "GET",
            f"/timesheets/{timesheet_id}",
            authenticated=True,
        )
        return TimesheetDetailResponse.model_validate(response.json())

    async def submit_timesheet(self, body: dict[str, object]) -> TimesheetSubmittedResponse:
        response = await self._request(
            "POST",
            "/timesheets",
            json=body,
            authenticated=True,
        )
        return TimesheetSubmittedResponse.model_validate(response.json())

    async def list_my_allocations(
        self, *, week_start: str | None = None
    ) -> MyAllocationListResponse | WeekAllocationContextResponse:
        params = {"week_start": week_start} if week_start else None
        response = await self._request(
            "GET",
            "/allocations/mine",
            params=params,
            authenticated=True,
        )
        payload = response.json()
        if week_start is not None:
            return WeekAllocationContextResponse.model_validate(payload)
        return MyAllocationListResponse.model_validate(payload)

    async def list_activity_tags(self) -> ActivityTagListResponse:
        response = await self._request(
            "GET",
            "/activity-tags",
            authenticated=True,
        )
        return ActivityTagListResponse.model_validate(response.json())

    async def get_employee_detail(
        self, employee_id: int
    ) -> DashboardEmployeeDetailResponse:
        response = await self._request(
            "GET",
            f"/dashboard/resources/{employee_id}",
            authenticated=True,
        )
        return DashboardEmployeeDetailResponse.model_validate(response.json())

    async def skill_match(
        self, *, requirement: str, project_id: int | None = None
    ) -> SkillMatchResponse:
        body: dict[str, object] = {"requirement": requirement}
        if project_id is not None:
            body["project_id"] = project_id
        response = await self._request(
            "POST",
            "/ai/skill-match",
            json=body,
            authenticated=True,
            timeout_seconds=self._settings.ai_request_timeout_seconds,
        )
        return SkillMatchResponse.model_validate(response.json())

    async def risk_summary(self, project_id: int) -> RiskSummaryResponse:
        response = await self._request(
            "POST",
            f"/ai/risk-summary/{project_id}",
            authenticated=True,
            timeout_seconds=self._settings.ai_request_timeout_seconds,
        )
        return RiskSummaryResponse.model_validate(response.json())

    async def team_build(
        self, *, requirement: str, project_id: int
    ) -> TeamBuildResponse:
        response = await self._request(
            "POST",
            "/ai/team-build",
            json={"requirement": requirement, "project_id": project_id},
            authenticated=True,
            timeout_seconds=self._settings.ai_request_timeout_seconds,
        )
        return TeamBuildResponse.model_validate(response.json())

    async def bulk_create_allocations(
        self, payload: BulkCreateAllocationRequest
    ) -> BulkAllocationCreatedResponse:
        response = await self._request(
            "POST",
            "/allocations/bulk",
            json=payload.model_dump(mode="json"),
            authenticated=True,
        )
        return BulkAllocationCreatedResponse.model_validate(response.json())

    def _auth_headers(self) -> dict[str, str]:
        try:
            token = self._session_manager.get_token()
        except SessionNotAuthenticatedError as exc:
            raise SessionNotAuthenticatedError("Not logged in") from exc
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        authenticated: bool = False,
        timeout_seconds: float | None = None,
    ) -> httpx.Response:
        headers = self._auth_headers() if authenticated else {}
        timeout = timeout_seconds or self._settings.request_timeout_seconds
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.api_base_url,
                timeout=timeout,
            ) as client:
                response = await client.request(
                    method, path, json=json, params=params, headers=headers
                )
        except httpx.RequestError as exc:
            raise NetworkError(
                "Cannot reach server. Is it running?"
            ) from exc

        if response.is_error:
            self._raise_api_error(response)
        return response

    def _raise_api_error(self, response: httpx.Response) -> None:
        try:
            error = ErrorBody.model_validate(response.json())
            detail = error.detail
            code = error.code
        except Exception:
            detail = "Request failed"
            code = "UnknownError"
        raise ApiRequestError(
            detail,
            status_code=response.status_code,
            code=code,
        )
