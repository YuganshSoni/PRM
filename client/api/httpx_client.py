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
from client.schemas.employee import (
    AssignManagerResponse,
    EmployeeActionResponse,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeUpsertResponse,
)
from client.schemas.allocation import AllocationListResponse
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
            f"/employees/by-user/{user_id}",
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
            "/employees",
            params=params,
            authenticated=True,
        )
        return EmployeeListResponse.model_validate(response.json())

    async def get_employee(self, employee_id: int) -> EmployeeDetailResponse:
        response = await self._request(
            "GET",
            f"/employees/{employee_id}",
            authenticated=True,
        )
        return EmployeeDetailResponse.model_validate(response.json())

    async def deactivate_employee(self, employee_id: int) -> EmployeeActionResponse:
        response = await self._request(
            "POST",
            f"/employees/{employee_id}/deactivate",
            authenticated=True,
        )
        return EmployeeActionResponse.model_validate(response.json())

    async def assign_manager(
        self, employee_user_id: int, manager_user_id: int
    ) -> AssignManagerResponse:
        response = await self._request(
            "PUT",
            "/employees/assign-manager",
            json={
                "employee_user_id": employee_user_id,
                "manager_user_id": manager_user_id,
            },
            authenticated=True,
        )
        return AssignManagerResponse.model_validate(response.json())

    async def list_employee_skills(self, employee_id: int) -> SkillListResponse:
        response = await self._request(
            "GET",
            f"/employees/{employee_id}/skills",
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
            f"/employees/{employee_id}/skills",
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

    async def get_employee_detail(
        self, employee_id: int
    ) -> DashboardEmployeeDetailResponse:
        response = await self._request(
            "GET",
            f"/dashboard/employees/{employee_id}",
            authenticated=True,
        )
        return DashboardEmployeeDetailResponse.model_validate(response.json())

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
    ) -> httpx.Response:
        headers = self._auth_headers() if authenticated else {}
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.api_base_url,
                timeout=self._settings.request_timeout_seconds,
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
