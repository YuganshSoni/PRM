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
    ManagerMilestoneResponse,
    ManagerProjectAllocationResponse,
    ManagerProjectDetailResponse,
    ProjectCreatedResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectRiskFlagResponse,
    ProjectSummaryResponse,
    ProjectUpdatedResponse,
)
from server.services.project_service import (
    ManagerProjectDetailResult,
    ProjectService,
)
from server.services.resource_mapper import ResourceMapper


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
            "/mine/{project_id}",
            self.get_manager_project_detail,
            methods=["GET"],
            response_model=ManagerProjectDetailResponse,
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
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
    ) -> ManagedProjectListResponse:
        result = await project_service.list_by_manager(_manager)
        return ManagedProjectListResponse(
            items=[
                ManagedProjectSummaryResponse(
                    id=row.id,
                    name=row.name,
                    status=row.status,
                    end_date=row.end_date,
                    health_status=row.health_status,
                    computed_at=row.computed_at,
                )
                for row in result.items
            ]
        )

    async def get_manager_project_detail(
        self,
        project_id: int,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        project_service: ProjectService = Depends(dependency_provider.get_project_service),
    ) -> ManagerProjectDetailResponse:
        detail = await project_service.get_manager_project_detail(
            _manager, project_id
        )
        return self._to_manager_detail(detail)

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
            manager_name=ResourceMapper.full_name(project.manager),
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
            manager_name=ResourceMapper.full_name(project.manager),
            total_story_points=project.total_story_points,
        )

    @staticmethod
    def _to_manager_detail(
        detail: ManagerProjectDetailResult,
    ) -> ManagerProjectDetailResponse:
        return ManagerProjectDetailResponse(
            id=detail.id,
            name=detail.name,
            end_date=detail.end_date,
            status=detail.status,
            health_status=detail.health_status,
            computed_at=detail.computed_at,
            risk_flags=[
                ProjectRiskFlagResponse(
                    flag_text=flag.flag_text,
                    is_positive=flag.is_positive,
                    sort_order=flag.sort_order,
                )
                for flag in detail.risk_flags
            ],
            milestones=[
                ManagerMilestoneResponse(
                    id=milestone.id,
                    title=milestone.title,
                    due_date=milestone.due_date,
                    story_points=milestone.story_points,
                    status=milestone.status,
                    sort_order=milestone.sort_order,
                    is_overdue=milestone.is_overdue,
                )
                for milestone in detail.milestones
            ],
            allocations=[
                ManagerProjectAllocationResponse(
                    resource_name=allocation.resource_name,
                    utilisation_percent=allocation.utilisation_percent,
                    from_date=allocation.from_date,
                    to_date=allocation.to_date,
                )
                for allocation in detail.allocations
            ],
        )
