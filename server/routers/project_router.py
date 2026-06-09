from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from server.core.dependencies import dependency_provider
from server.models.enums import ProjectStatus, UserRole
from server.models.project import Project
from server.models.user import User
from server.schemas.requests.project import CreateProjectRequest, UpdateProjectRequest
from server.schemas.response_values import ProjectMessage
from server.schemas.responses.project import (
    ManagedProjectListResponse,
    ManagedProjectSummaryResponse,
    ProjectCreatedResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSummaryResponse,
    ProjectUpdatedResponse,
)
from server.services.allocation_service import AllocationService
from server.services.project_service import ProjectService


class ProjectRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/projects", tags=["projects"])
        self.router.add_api_route(
            "",
            self.create_project,
            methods=["POST"],
            response_model=ProjectCreatedResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "",
            self.list_projects,
            methods=["GET"],
            response_model=ProjectListResponse,
        )
        self.router.add_api_route(
            "/mine",
            self.list_managed_projects,
            methods=["GET"],
            response_model=ManagedProjectListResponse,
        )
        self.router.add_api_route(
            "/{project_id}",
            self.get_project,
            methods=["GET"],
            response_model=ProjectDetailResponse,
        )
        self.router.add_api_route(
            "/{project_id}",
            self.update_project,
            methods=["PUT"],
            response_model=ProjectUpdatedResponse,
        )

    async def create_project(
        self,
        body: CreateProjectRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
    ) -> ProjectCreatedResponse:
        project = await project_service.create_project(body)
        return ProjectCreatedResponse(
            id=project.id,
            name=project.name,
            status=ProjectStatus(project.status),
            message=ProjectMessage.PROJECT_CREATED,
        )

    async def list_projects(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
        status_filter: ProjectStatus | None = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> ProjectListResponse:
        result = await project_service.list_projects(
            status=status_filter, limit=limit, offset=offset
        )
        items = []
        for project in result.items:
            done = await project_service.story_points_done(project.id)
            items.append(self._to_summary(project, done))
        return ProjectListResponse(
            items=items,
            total=result.total,
            limit=limit,
            offset=offset,
        )

    async def list_managed_projects(
        self,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        allocation_service: AllocationService = Depends(
            dependency_provider.get_allocation_service
        ),
    ) -> ManagedProjectListResponse:
        projects = await allocation_service.list_managed_projects(_manager)
        return ManagedProjectListResponse(
            items=[
                ManagedProjectSummaryResponse(
                    id=project.id,
                    name=project.name,
                    status=ProjectStatus(project.status),
                )
                for project in projects
            ]
        )

    async def get_project(
        self,
        project_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
    ) -> ProjectDetailResponse:
        project = await project_service.get_project(project_id)
        return self._to_detail(project)

    async def update_project(
        self,
        project_id: int,
        body: UpdateProjectRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
    ) -> ProjectUpdatedResponse:
        await project_service.update_project(project_id, body)
        return ProjectUpdatedResponse(
            id=project_id,
            message=ProjectMessage.PROJECT_UPDATED,
        )

    def _to_summary(self, project: Project, story_points_done: int) -> ProjectSummaryResponse:
        return ProjectSummaryResponse(
            id=project.id,
            name=project.name,
            manager_name=project.manager.full_name,
            end_date=project.end_date,
            status=ProjectStatus(project.status),
            story_points_done=story_points_done,
            story_points_total=project.total_story_points,
        )

    def _to_detail(self, project: Project) -> ProjectDetailResponse:
        return ProjectDetailResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            status=ProjectStatus(project.status),
            manager_id=project.manager_id,
            manager_name=project.manager.full_name,
            total_story_points=project.total_story_points,
        )
