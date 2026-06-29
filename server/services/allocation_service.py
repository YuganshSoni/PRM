from datetime import date

from server.core.exceptions import (
    AllocationNotFoundError,
    EmployeeNotAllocatableError,
    EmployeeNotFoundError,
    InvalidAllocationDatesError,
    InvalidProjectStatusForAllocationError,
    ManagerProfileNotFoundError,
    NotProjectOwnerError,
    OverAllocationError,
    ProjectNotFoundError,
    ResourceStatusNotFoundError,
)
from server.models.allocation import Allocation
from server.models.resource import Resource
from server.models.enums import ResourceStatusEnum, ProjectStatus
from server.models.project import Project
from server.models.user import User
from decimal import Decimal

from server.core.exceptions import EmployeeProfileNotFoundError, SystemConfigNotFoundError
from server.core.week_utils import WeekCalculator
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.resource_status_repository import ResourceStatusRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.schemas.requests.allocation import (
    BulkCreateAllocationRequest,
    CreateAllocationRequest,
)
from server.schemas.responses.allocation import (
    BulkAllocationCreatedItemResponse,
    BulkAllocationCreatedResponse,
    MyAllocationListResponse,
    MyAllocationSummaryResponse,
    WeekAllocationContextResponse,
    WeekProjectAllocationResponse,
)
from server.services.resource_mapper import ResourceMapper
from server.schemas.response_values import AllocationMessage
from server.notifications.services.allocation_notification_service import (
    AllocationNotificationService,
)
from server.services.scheduler_results import RecomputeResult


class AllocationService:
    _ALLOWED_PROJECT_STATUSES = frozenset(
        {ProjectStatus.PLANNED, ProjectStatus.ACTIVE}
    )

    def __init__(
        self,
        resource_repository: ResourceRepository,
        project_repository: ProjectRepository,
        allocation_repository: AllocationRepository,
        system_config_repository: SystemConfigRepository,
        resource_status_repository: ResourceStatusRepository,
        allocation_notification_service: AllocationNotificationService | None = None,
    ) -> None:
        self._resource_repository = resource_repository
        self._project_repository = project_repository
        self._allocation_repository = allocation_repository
        self._system_config_repository = system_config_repository
        self._resource_status_repository = resource_status_repository
        self._allocation_notification_service = allocation_notification_service

    async def create_allocation(
        self, dto: CreateAllocationRequest, user: User
    ) -> Allocation:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        resource = await self._resource_repository.get_by_id_with_user(
            dto.resource_id
        )
        if resource is None:
            raise EmployeeNotFoundError("Resource not found")
        self._ensure_resource_on_team(resource, manager_resource_id)

        project = await self._project_repository.get_by_id_with_manager(
            dto.project_id
        )
        if project is None:
            raise ProjectNotFoundError("Project not found")
        self._ensure_project_allows_allocation(project)

        if dto.from_date >= dto.to_date:
            raise InvalidAllocationDatesError("From date must be before to date")

        await self.validate_utilisation(
            dto.resource_id,
            dto.from_date,
            dto.to_date,
            dto.utilisation_percent,
        )

        allocation = Allocation(
            resource_id=dto.resource_id,
            project_id=dto.project_id,
            utilisation_percent=dto.utilisation_percent,
            from_date=dto.from_date,
            to_date=dto.to_date,
        )
        saved = await self._allocation_repository.save(allocation)

        await self._apply_resource_status(resource, ResourceStatusEnum.ALLOCATED)

        saved.resource = resource
        saved.project = project
        if self._allocation_notification_service is not None:
            await self._allocation_notification_service.send_allocation_confirmation(
                saved
            )
        return saved

    async def bulk_create(
        self, dto: BulkCreateAllocationRequest, user: User
    ) -> BulkAllocationCreatedResponse:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        project = await self._project_repository.get_by_id_with_manager(dto.project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        if project.manager_id != manager_resource_id:
            raise NotProjectOwnerError("Only project owner can create allocations")
        self._ensure_project_allows_allocation(project)

        if dto.from_date >= dto.to_date:
            raise InvalidAllocationDatesError("From date must be before to date")

        resources: list[Resource] = []
        for item in dto.items:
            resource = await self._resource_repository.get_by_id_with_user(
                item.resource_id
            )
            if resource is None:
                raise EmployeeNotFoundError("Resource not found")
            self._ensure_resource_on_team(resource, manager_resource_id)
            resources.append(resource)

        for item in dto.items:
            await self.validate_utilisation(
                item.resource_id,
                dto.from_date,
                dto.to_date,
                dto.utilisation_percent,
            )

        saved_allocations: list[tuple[Allocation, Resource, str | None]] = []
        for item, resource in zip(dto.items, resources, strict=True):
            allocation = Allocation(
                resource_id=item.resource_id,
                project_id=dto.project_id,
                utilisation_percent=dto.utilisation_percent,
                from_date=dto.from_date,
                to_date=dto.to_date,
            )
            saved = await self._allocation_repository.save(allocation)
            await self._apply_resource_status(resource, ResourceStatusEnum.ALLOCATED)
            saved_allocations.append((saved, resource, item.role_key))

        if self._allocation_notification_service is not None:
            for saved, _resource, _role_key in saved_allocations:
                await self._allocation_notification_service.send_allocation_confirmation(
                    saved
                )

        return BulkAllocationCreatedResponse(
            project_id=dto.project_id,
            project_name=project.name,
            message=AllocationMessage.ALLOCATION_CREATED,
            items=[
                BulkAllocationCreatedItemResponse(
                    id=allocation.id,
                    resource_id=allocation.resource_id,
                    resource_name=ResourceMapper.full_name(resource),
                    role_key=role_key,
                    utilisation_percent=allocation.utilisation_percent,
                    from_date=allocation.from_date,
                    to_date=allocation.to_date,
                )
                for allocation, resource, role_key in saved_allocations
            ],
        )

    async def end_allocation(self, allocation_id: int, user: User) -> Allocation:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        allocation = await self._allocation_repository.get_by_id_with_relations(
            allocation_id
        )
        if allocation is None:
            raise AllocationNotFoundError("Allocation not found")

        if allocation.project.manager_id != manager_resource_id:
            raise NotProjectOwnerError("Only project owner can end allocations")

        today = date.today()
        allocation.to_date = today
        await self._allocation_repository.save(allocation)

        await self._recompute_resource_status_after_end(
            allocation.resource_id,
            exclude_allocation_id=allocation.id,
        )
        reloaded = await self._allocation_repository.get_by_id_with_relations(
            allocation_id
        )
        if reloaded is None:
            raise AllocationNotFoundError("Allocation not found")
        return reloaded

    async def validate_utilisation(
        self,
        resource_id: int,
        from_date: date,
        to_date: date,
        utilisation_percent: int,
    ) -> None:
        overlapping = await self._allocation_repository.find_overlapping(
            resource_id, from_date, to_date
        )
        current_total = sum(item.utilisation_percent for item in overlapping)
        proposed_total = current_total + utilisation_percent
        if proposed_total > 100:
            raise OverAllocationError(
                f"Total utilisation would be {proposed_total}%"
            )

    async def list_project_allocations(
        self, project_id: int, user: User
    ) -> tuple[Project, list[Allocation]]:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        if project.manager_id != manager_resource_id:
            raise NotProjectOwnerError("Only project owner can view project allocations")

        allocations = await self._allocation_repository.find_active_by_project(
            project_id
        )
        return project, allocations

    async def list_managed_projects(self, user: User) -> list[Project]:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        return await self._project_repository.find_by_manager_id(manager_resource_id)

    async def list_my_allocations(
        self, user: User, *, week_start: date | None = None
    ) -> MyAllocationListResponse | WeekAllocationContextResponse:
        resource_id = await self._resolve_resource_id(user)

        if week_start is not None:
            WeekCalculator.validate_monday(week_start)
            config = await self._system_config_repository.get()
            if config is None:
                raise SystemConfigNotFoundError("System configuration not found")

            allocations = (
                await self._allocation_repository.find_active_for_resource_in_week(
                    resource_id, week_start
                )
            )
            max_weekly = Decimal(config.max_weekly_hours)
            project_rows: dict[int, dict[str, object]] = {}
            for allocation in allocations:
                project_id = allocation.project_id
                if project_id not in project_rows:
                    project_rows[project_id] = {
                        "project_name": allocation.project.name,
                        "utilisation_percent": allocation.utilisation_percent,
                    }
                else:
                    project_rows[project_id]["utilisation_percent"] = (
                        int(project_rows[project_id]["utilisation_percent"])
                        + allocation.utilisation_percent
                    )

            projects = [
                WeekProjectAllocationResponse(
                    project_id=project_id,
                    project_name=str(data["project_name"]),
                    utilisation_percent=int(data["utilisation_percent"]),
                    max_hours=float(
                        Decimal(int(data["utilisation_percent"]))
                        / Decimal(100)
                        * max_weekly
                    ),
                )
                for project_id, data in sorted(project_rows.items())
            ]
            return WeekAllocationContextResponse(
                week_start=week_start,
                max_weekly_hours=config.max_weekly_hours,
                projects=projects,
            )

        allocations = await self._allocation_repository.find_active_by_resource(
            resource_id
        )
        total_utilisation = sum(
            allocation.utilisation_percent for allocation in allocations
        )
        return MyAllocationListResponse(
            items=[
                MyAllocationSummaryResponse(
                    project_name=allocation.project.name,
                    utilisation_percent=allocation.utilisation_percent,
                    from_date=allocation.from_date,
                    to_date=allocation.to_date,
                    status="ACTIVE",
                )
                for allocation in allocations
            ],
            total_utilisation_percent=total_utilisation,
        )

    async def recompute_all_resource_statuses(self) -> RecomputeResult:
        resources = await self._resource_repository.list_active()
        active_allocations = await self._allocation_repository.find_all_active()
        allocated_ids = {allocation.resource_id for allocation in active_allocations}

        bench_count = 0
        allocated_count = 0
        for resource in resources:
            status = (
                ResourceStatusEnum.ALLOCATED
                if resource.id in allocated_ids
                else ResourceStatusEnum.BENCH
            )
            await self._apply_resource_status(resource, status)
            if status == ResourceStatusEnum.BENCH:
                bench_count += 1
            else:
                allocated_count += 1

        return RecomputeResult(
            bench_count=bench_count,
            allocated_count=allocated_count,
        )

    async def compute_utilisation(self, resource_id: int, _today: date) -> int:
        allocations = await self._allocation_repository.find_active_by_resource(
            resource_id
        )
        return sum(allocation.utilisation_percent for allocation in allocations)

    async def _resolve_resource_id(self, user: User) -> int:
        resource = await self._resource_repository.find_by_user_id(user.id)
        if resource is None:
            raise EmployeeProfileNotFoundError(
                "Resource user does not have an resource profile"
            )
        return resource.id

    async def _resolve_manager_resource_id(self, user: User) -> int:
        manager_resource = await self._resource_repository.find_by_user_id(user.id)
        if manager_resource is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an resource profile"
            )
        return manager_resource.id

    def _ensure_resource_on_team(
        self, resource: Resource, manager_resource_id: int
    ) -> None:
        if not resource.is_active or resource.manager_id != manager_resource_id:
            raise EmployeeNotAllocatableError("Resource not in your team")

    def _ensure_project_allows_allocation(self, project: Project) -> None:
        if ProjectStatus(project.status) not in self._ALLOWED_PROJECT_STATUSES:
            raise InvalidProjectStatusForAllocationError(
                "Project must be PLANNED or ACTIVE"
            )

    async def _recompute_resource_status_after_end(
        self,
        resource_id: int,
        *,
        exclude_allocation_id: int,
    ) -> None:
        resource = await self._resource_repository.get_by_id_with_user(resource_id)
        if resource is None:
            return

        remaining = await self._allocation_repository.find_active_by_resource(
            resource_id
        )
        remaining = [
            item for item in remaining if item.id != exclude_allocation_id
        ]
        status = (
            ResourceStatusEnum.BENCH if not remaining else ResourceStatusEnum.ALLOCATED
        )
        await self._apply_resource_status(resource, status)

    async def _apply_resource_status(
        self, resource: Resource, status: ResourceStatusEnum
    ) -> None:
        status_row = await self._resource_status_repository.find_by_name(status.value)
        if status_row is None:
            raise ResourceStatusNotFoundError(
                f"Resource status {status.value} not found"
            )
        resource.resource_status_id = status_row.id
        await self._resource_repository.save(resource)
