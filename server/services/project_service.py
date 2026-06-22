from dataclasses import dataclass
from datetime import date, datetime

from server.core.exceptions import (
    EmployeeNotFoundError,
    InvalidManagerRoleError,
    InvalidProjectDatesError,
    InvalidProjectManagerError,
    InvalidProjectStatusError,
    InvalidStoryPointsError,
    ManagerProfileNotFoundError,
    ProjectNotFoundError,
)
from server.core.user_role import user_role_enum
from server.models.allocation import Allocation
from server.models.enums import HealthStatus, MilestoneStatus, ProjectStatus, UserRole
from server.models.milestone import Milestone
from server.models.project import Project
from server.models.user import User
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.resource_repository import ResourceRepository
from server.schemas.requests.project import CreateProjectRequest, UpdateProjectRequest
from server.services.project_health_service import (
    ProjectHealthService,
    ProjectHealthSnapshot,
    RiskFlagView,
)


@dataclass(frozen=True)
class ProjectListResult:
    items: list[Project]
    total: int


@dataclass(frozen=True)
class ManagedProjectSummaryRow:
    id: int
    name: str
    status: ProjectStatus
    end_date: date
    health_status: HealthStatus | None
    computed_at: datetime | None


@dataclass(frozen=True)
class ManagedProjectListResult:
    items: list[ManagedProjectSummaryRow]


@dataclass(frozen=True)
class ManagerMilestoneRow:
    id: int
    title: str
    due_date: date
    story_points: int
    status: MilestoneStatus
    sort_order: int
    is_overdue: bool


@dataclass(frozen=True)
class ManagerAllocationRow:
    resource_name: str
    utilisation_percent: int
    from_date: date
    to_date: date


@dataclass(frozen=True)
class ManagerProjectDetailResult:
    id: int
    name: str
    end_date: date
    status: ProjectStatus
    health_status: HealthStatus | None
    computed_at: datetime | None
    risk_flags: list[RiskFlagView]
    milestones: list[ManagerMilestoneRow]
    allocations: list[ManagerAllocationRow]


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        resource_repository: ResourceRepository,
        milestone_repository: MilestoneRepository,
        allocation_repository: AllocationRepository,
        project_health_service: ProjectHealthService,
    ) -> None:
        self._project_repository = project_repository
        self._resource_repository = resource_repository
        self._milestone_repository = milestone_repository
        self._allocation_repository = allocation_repository
        self._project_health_service = project_health_service

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

    async def list_by_manager(self, user: User) -> ManagedProjectListResult:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        projects = await self._project_repository.find_by_manager_id(
            manager_resource_id
        )
        health_map = await self._project_health_service.get_snapshots_for_projects(
            [project.id for project in projects]
        )
        items = [
            self._to_managed_summary(project, health_map.get(project.id))
            for project in projects
        ]
        return ManagedProjectListResult(items=items)

    async def get_manager_project_detail(
        self, user: User, project_id: int
    ) -> ManagerProjectDetailResult:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None or project.manager_id != manager_resource_id:
            raise ProjectNotFoundError("Project not found")

        snapshot = await self._project_health_service.get_snapshot(project_id)
        risk_flags = await self._project_health_service.get_risk_flags_for_project(
            project_id
        )
        milestones = await self._milestone_repository.find_by_project_id(project_id)
        allocations = await self._allocation_repository.find_active_by_project(
            project_id
        )
        today = date.today()

        return ManagerProjectDetailResult(
            id=project.id,
            name=project.name,
            end_date=project.end_date,
            status=ProjectStatus(project.status),
            health_status=snapshot.health_status if snapshot else None,
            computed_at=snapshot.computed_at if snapshot else None,
            risk_flags=risk_flags,
            milestones=[
                self._to_milestone_row(milestone, today) for milestone in milestones
            ],
            allocations=[
                self._to_allocation_row(allocation) for allocation in allocations
            ],
        )

    async def _resolve_manager_resource_id(self, user: User) -> int:
        resource = await self._resource_repository.find_by_user_id(user.id)
        if resource is None:
            raise ManagerProfileNotFoundError("Manager profile not found")
        return resource.id

    async def _validate_manager(self, manager_id: int) -> None:
        manager = await self._resource_repository.get_by_id_with_user(manager_id)
        if manager is None:
            raise EmployeeNotFoundError("Manager resource not found")
        if not manager.is_active:
            raise InvalidProjectManagerError("Manager resource is inactive")
        if user_role_enum(manager.user) != UserRole.MANAGER:
            raise InvalidManagerRoleError("Manager must have MANAGER role")

    def _validate_dates(self, start_date, end_date) -> None:
        if start_date >= end_date:
            raise InvalidProjectDatesError("Start date must be before end date")

    def _validate_story_points(self, total_story_points: int) -> None:
        if total_story_points < 0:
            raise InvalidStoryPointsError("Total story points cannot be negative")

    @staticmethod
    def _to_managed_summary(
        project: Project,
        snapshot: ProjectHealthSnapshot | None,
    ) -> ManagedProjectSummaryRow:
        return ManagedProjectSummaryRow(
            id=project.id,
            name=project.name,
            status=ProjectStatus(project.status),
            end_date=project.end_date,
            health_status=snapshot.health_status if snapshot else None,
            computed_at=snapshot.computed_at if snapshot else None,
        )

    @staticmethod
    def _to_milestone_row(milestone: Milestone, today: date) -> ManagerMilestoneRow:
        status = MilestoneStatus(milestone.status)
        is_overdue = milestone.due_date < today and status != MilestoneStatus.DONE
        return ManagerMilestoneRow(
            id=milestone.id,
            title=milestone.title,
            due_date=milestone.due_date,
            story_points=milestone.story_points,
            status=MilestoneStatus(milestone.status),
            sort_order=milestone.sort_order,
            is_overdue=is_overdue,
        )

    @staticmethod
    def _to_allocation_row(allocation: Allocation) -> ManagerAllocationRow:
        resource = allocation.resource
        user = getattr(resource, "user", None)
        resource_name = user.full_name if user is not None else "Resource"
        return ManagerAllocationRow(
            resource_name=resource_name,
            utilisation_percent=allocation.utilisation_percent,
            from_date=allocation.from_date,
            to_date=allocation.to_date,
        )
