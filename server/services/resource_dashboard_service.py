from collections import defaultdict
from datetime import datetime

from server.core.exceptions import (
    EmployeeNotFoundError,
    ForbiddenError,
    ManagerProfileNotFoundError,
)
from server.models.allocation import Allocation
from server.models.employee import Employee
from server.models.employee_skill import EmployeeSkill
from server.models.enums import EmployeeStatus
from server.models.user import User
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.employee_repository import EmployeeRepository
from server.repositories.skill_repository import SkillRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.schemas.responses.dashboard import (
    ActiveEmployeeSummary,
    BenchEmployeeSummary,
    DashboardAllocationSummary,
    DashboardEmployeeDetailResponse,
    DashboardStatsResponse,
    ResourceDashboardResponse,
)


class ResourceDashboardService:
    def __init__(
        self,
        employee_repository: EmployeeRepository,
        allocation_repository: AllocationRepository,
        skill_repository: SkillRepository,
        timesheet_repository: TimesheetRepository,
    ) -> None:
        self._employee_repository = employee_repository
        self._allocation_repository = allocation_repository
        self._skill_repository = skill_repository
        self._timesheet_repository = timesheet_repository

    async def get_resource_dashboard(self, user: User) -> ResourceDashboardResponse:
        manager_employee_id = await self._resolve_manager_employee_id(user)

        bench_employees = await self._employee_repository.find_by_manager_and_status(
            manager_employee_id,
            EmployeeStatus.BENCH,
            load_skills=True,
        )
        team_allocations = await self._allocation_repository.find_active_by_team(
            manager_employee_id
        )
        utilisation_by_employee = self._sum_utilisation_by_employee(team_allocations)

        active_employees: list[ActiveEmployeeSummary] = []
        partial_count = 0
        for employee_id in sorted(utilisation_by_employee):
            total_util = utilisation_by_employee[employee_id]
            if total_util <= 0:
                continue
            employee = next(
                allocation.employee
                for allocation in team_allocations
                if allocation.employee_id == employee_id
            )
            active_employees.append(
                ActiveEmployeeSummary(
                    id=employee.id,
                    full_name=employee.full_name,
                    utilisation_percent=total_util,
                    availability_label=self._availability_label(total_util),
                )
            )
            if 0 < total_util < 100:
                partial_count += 1

        return ResourceDashboardResponse(
            bench_employees=[
                BenchEmployeeSummary(
                    id=employee.id,
                    full_name=employee.full_name,
                    department=employee.department,
                    skills=self._skill_names(employee.skills),
                )
                for employee in bench_employees
            ],
            active_employees=active_employees,
            stats=DashboardStatsResponse(
                bench_count=len(bench_employees),
                partial_count=partial_count,
            ),
            month_label=datetime.now().strftime("%B %Y"),
        )

    async def get_employee_detail(
        self, employee_id: int, user: User
    ) -> DashboardEmployeeDetailResponse:
        manager_employee_id = await self._resolve_manager_employee_id(user)

        employee = await self._employee_repository.get_by_id_with_user(employee_id)
        if employee is None:
            raise EmployeeNotFoundError("Employee not found")
        if employee.manager_id != manager_employee_id:
            raise ForbiddenError("Employee not in your team")

        skills = await self._skill_repository.find_by_employee_id(employee_id)
        allocations = await self._allocation_repository.find_active_by_employee(
            employee_id
        )
        total_util = sum(allocation.utilisation_percent for allocation in allocations)
        recent_tags = await self._timesheet_repository.find_recent_activity_tags(
            employee_id
        )

        return DashboardEmployeeDetailResponse(
            id=employee.id,
            full_name=employee.full_name,
            department=employee.department,
            status=EmployeeStatus(employee.status),
            utilisation_percent=total_util,
            skills=[skill.skill_name for skill in skills],
            active_allocations=[
                DashboardAllocationSummary(
                    project_name=allocation.project.name,
                    utilisation_percent=allocation.utilisation_percent,
                    from_date=allocation.from_date,
                    to_date=allocation.to_date,
                )
                for allocation in allocations
            ],
            recent_activity_tags=recent_tags,
        )

    async def _resolve_manager_employee_id(self, user: User) -> int:
        manager_employee = await self._employee_repository.find_by_user_id(user.id)
        if manager_employee is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an employee profile"
            )
        return manager_employee.id

    @staticmethod
    def _sum_utilisation_by_employee(
        allocations: list[Allocation],
    ) -> dict[int, int]:
        totals: dict[int, int] = defaultdict(int)
        for allocation in allocations:
            totals[allocation.employee_id] += allocation.utilisation_percent
        return dict(totals)

    @staticmethod
    def _availability_label(total_util: int) -> str:
        if total_util >= 100:
            return "FULL"
        return f"{100 - total_util}% free"

    @staticmethod
    def _skill_names(skills: list[EmployeeSkill]) -> list[str]:
        return [skill.skill_name for skill in skills]
