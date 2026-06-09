from dataclasses import dataclass

from server.core.exceptions import (
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidProjectDatesError,
    InvalidProjectManagerError,
    InvalidProjectStatusError,
    InvalidStoryPointsError,
    ProjectNotFoundError,
)
from server.models.enums import ProjectStatus, UserRole
from server.models.project import Project
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.schemas.requests.project import CreateProjectRequest, UpdateProjectRequest


@dataclass(frozen=True)
class ProjectListResult:
    items: list[Project]
    total: int


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        employee_repository: EmployeeRepository,
        milestone_repository: MilestoneRepository,
    ) -> None:
        self._project_repository = project_repository
        self._employee_repository = employee_repository
        self._milestone_repository = milestone_repository

    async def create_project(self, dto: CreateProjectRequest) -> Project:
        self._validate_dates(dto.start_date, dto.end_date)
        self._validate_story_points(dto.total_story_points)
        if dto.status == ProjectStatus.COMPLETED:
            raise InvalidProjectStatusError(
                "COMPLETED status is not allowed when creating a project"
            )
        await self._validate_manager(dto.manager_id)

        project = Project(
            name=dto.name,
            description=dto.description,
            start_date=dto.start_date,
            end_date=dto.end_date,
            status=dto.status,
            manager_id=dto.manager_id,
            total_story_points=dto.total_story_points,
        )
        return await self._project_repository.save(project)

    async def update_project(
        self, project_id: int, dto: UpdateProjectRequest
    ) -> Project:
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")

        self._validate_dates(dto.start_date, dto.end_date)
        self._validate_story_points(dto.total_story_points)
        await self._validate_manager(dto.manager_id)

        project.name = dto.name
        project.description = dto.description
        project.start_date = dto.start_date
        project.end_date = dto.end_date
        project.status = dto.status
        project.manager_id = dto.manager_id
        project.total_story_points = dto.total_story_points
        return await self._project_repository.save(project)

    async def list_projects(
        self,
        *,
        status: ProjectStatus | None,
        limit: int,
        offset: int,
    ) -> ProjectListResult:
        items = await self._project_repository.list_projects(
            status=status, limit=limit, offset=offset
        )
        total = await self._project_repository.count_projects(status=status)
        return ProjectListResult(items=items, total=total)

    async def get_project(self, project_id: int) -> Project:
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def story_points_done(self, project_id: int) -> int:
        return await self._milestone_repository.sum_done_story_points(project_id)

    async def _validate_manager(self, manager_id: int) -> None:
        manager = await self._employee_repository.get_by_id_with_user(manager_id)
        if manager is None:
            raise EmployeeNotFoundError("Manager employee not found")
        if not manager.is_active:
            raise InvalidProjectManagerError("Manager employee is inactive")
        if manager.user.role != UserRole.MANAGER:
            raise InvalidManagerRoleError("Manager must have MANAGER role")

    def _validate_dates(self, start_date, end_date) -> None:
        if start_date >= end_date:
            raise InvalidProjectDatesError("Start date must be before end date")

    def _validate_story_points(self, total_story_points: int) -> None:
        if total_story_points < 0:
            raise InvalidStoryPointsError("Total story points cannot be negative")
