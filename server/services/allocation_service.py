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
)
from server.models.allocation import Allocation
from server.models.employee import Employee
from server.models.enums import EmployeeStatus, ProjectStatus
from server.models.project import Project
from server.models.user import User
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.project_repository import ProjectRepository
from server.schemas.requests.allocation import CreateAllocationRequest


class AllocationService:
    _ALLOWED_PROJECT_STATUSES = frozenset(
        {ProjectStatus.PLANNED, ProjectStatus.ACTIVE}
    )

    def __init__(
        self,
        employee_repository: EmployeeRepository,
        project_repository: ProjectRepository,
        allocation_repository: AllocationRepository,
    ) -> None:
        self._employee_repository = employee_repository
        self._project_repository = project_repository
        self._allocation_repository = allocation_repository

    async def create_allocation(
        self, dto: CreateAllocationRequest, user: User
    ) -> Allocation:
        manager_employee_id = await self._resolve_manager_employee_id(user)

        employee = await self._employee_repository.get_by_id_with_user(
            dto.employee_id
        )
        if employee is None:
            raise EmployeeNotFoundError("Employee not found")
        self._ensure_employee_on_team(employee, manager_employee_id)

        project = await self._project_repository.get_by_id_with_manager(
            dto.project_id
        )
        if project is None:
            raise ProjectNotFoundError("Project not found")
        self._ensure_project_allows_allocation(project)

        if dto.from_date >= dto.to_date:
            raise InvalidAllocationDatesError("From date must be before to date")

        await self.validate_utilisation(
            dto.employee_id,
            dto.from_date,
            dto.to_date,
            dto.utilisation_percent,
        )

        allocation = Allocation(
            employee_id=dto.employee_id,
            project_id=dto.project_id,
            utilisation_percent=dto.utilisation_percent,
            from_date=dto.from_date,
            to_date=dto.to_date,
        )
        saved = await self._allocation_repository.save(allocation)

        employee.status = EmployeeStatus.ALLOCATED
        await self._employee_repository.save(employee)

        saved.employee = employee
        saved.project = project
        return saved

    async def end_allocation(self, allocation_id: int, user: User) -> Allocation:
        manager_employee_id = await self._resolve_manager_employee_id(user)

        allocation = await self._allocation_repository.get_by_id_with_relations(
            allocation_id
        )
        if allocation is None:
            raise AllocationNotFoundError("Allocation not found")

        if allocation.project.manager_id != manager_employee_id:
            raise NotProjectOwnerError("Only project owner can end allocations")

        today = date.today()
        allocation.to_date = today
        await self._allocation_repository.save(allocation)

        await self._recompute_employee_status_after_end(
            allocation.employee_id,
            exclude_allocation_id=allocation.id,
        )
        return allocation

    async def validate_utilisation(
        self,
        employee_id: int,
        from_date: date,
        to_date: date,
        utilisation_percent: int,
    ) -> None:
        overlapping = await self._allocation_repository.find_overlapping(
            employee_id, from_date, to_date
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
        manager_employee_id = await self._resolve_manager_employee_id(user)

        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        if project.manager_id != manager_employee_id:
            raise NotProjectOwnerError("Only project owner can view project allocations")

        allocations = await self._allocation_repository.find_active_by_project(
            project_id
        )
        return project, allocations

    async def list_managed_projects(self, user: User) -> list[Project]:
        manager_employee_id = await self._resolve_manager_employee_id(user)
        return await self._project_repository.find_by_manager_id(manager_employee_id)

    async def _resolve_manager_employee_id(self, user: User) -> int:
        manager_employee = await self._employee_repository.find_by_user_id(user.id)
        if manager_employee is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an employee profile"
            )
        return manager_employee.id

    def _ensure_employee_on_team(
        self, employee: Employee, manager_employee_id: int
    ) -> None:
        if not employee.is_active or employee.manager_id != manager_employee_id:
            raise EmployeeNotAllocatableError("Employee not in your team")

    def _ensure_project_allows_allocation(self, project: Project) -> None:
        if ProjectStatus(project.status) not in self._ALLOWED_PROJECT_STATUSES:
            raise InvalidProjectStatusForAllocationError(
                "Project must be PLANNED or ACTIVE"
            )

    async def _recompute_employee_status_after_end(
        self,
        employee_id: int,
        *,
        exclude_allocation_id: int,
    ) -> None:
        employee = await self._employee_repository.get_by_id_with_user(employee_id)
        if employee is None:
            return

        remaining = await self._allocation_repository.find_active_by_employee(
            employee_id
        )
        remaining = [
            item for item in remaining if item.id != exclude_allocation_id
        ]
        employee.status = (
            EmployeeStatus.BENCH if not remaining else EmployeeStatus.ALLOCATED
        )
        await self._employee_repository.save(employee)
