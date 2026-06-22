from collections import defaultdict
from datetime import datetime

from server.core.exceptions import (
    EmployeeNotFoundError,
    ForbiddenError,
    ManagerProfileNotFoundError,
)
from server.models.allocation import Allocation
from server.models.enums import ResourceStatusEnum
from server.models.resource import Resource
from server.models.resource_skill import ResourceSkill
from server.models.user import User
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
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
from server.services.resource_mapper import ResourceMapper


class ResourceDashboardService:
    def __init__(
        self,
        resource_repository: ResourceRepository,
        allocation_repository: AllocationRepository,
        skill_repository: SkillRepository,
        timesheet_repository: TimesheetRepository,
    ) -> None:
        self._resource_repository = resource_repository
        self._allocation_repository = allocation_repository
        self._skill_repository = skill_repository
        self._timesheet_repository = timesheet_repository

    async def get_resource_dashboard(self, user: User) -> ResourceDashboardResponse:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        bench_resources = await self._resource_repository.find_by_manager_and_status(
            manager_resource_id,
            ResourceStatusEnum.BENCH,
            load_skills=True,
        )
        team_allocations = await self._allocation_repository.find_active_by_team(
            manager_resource_id
        )
        utilisation_by_resource = self._sum_utilisation_by_resource(team_allocations)

        active_resources: list[ActiveEmployeeSummary] = []
        partial_count = 0
        for resource_id in sorted(utilisation_by_resource):
            total_util = utilisation_by_resource[resource_id]
            if total_util <= 0:
                continue
            resource = next(
                allocation.resource
                for allocation in team_allocations
                if allocation.resource_id == resource_id
            )
            active_resources.append(
                ActiveEmployeeSummary(
                    id=resource.id,
                    full_name=ResourceMapper.full_name(resource),
                    utilisation_percent=total_util,
                    availability_label=self._availability_label(total_util),
                )
            )
            if 0 < total_util < 100:
                partial_count += 1

        return ResourceDashboardResponse(
            bench_resources=[
                BenchEmployeeSummary(
                    id=resource.id,
                    full_name=ResourceMapper.full_name(resource),
                    department=ResourceMapper.department_name(resource),
                    skills=self._skill_names(resource.skills),
                )
                for resource in bench_resources
            ],
            active_resources=active_resources,
            stats=DashboardStatsResponse(
                bench_count=len(bench_resources),
                partial_count=partial_count,
            ),
            month_label=datetime.now().strftime("%B %Y"),
        )

    async def get_resource_detail(
        self, resource_id: int, user: User
    ) -> DashboardEmployeeDetailResponse:
        manager_resource_id = await self._resolve_manager_resource_id(user)

        resource = await self._resource_repository.get_by_id_with_user(resource_id)
        if resource is None:
            raise EmployeeNotFoundError("Resource not found")
        if resource.manager_id != manager_resource_id:
            raise ForbiddenError("Resource not in your team")

        skills = await self._skill_repository.find_by_resource_id(resource_id)
        allocations = await self._allocation_repository.find_active_by_resource(
            resource_id
        )
        total_util = sum(allocation.utilisation_percent for allocation in allocations)
        recent_tags = await self._timesheet_repository.find_recent_activity_tags(
            resource_id
        )

        return DashboardEmployeeDetailResponse(
            id=resource.id,
            full_name=ResourceMapper.full_name(resource),
            department=ResourceMapper.department_name(resource),
            status=ResourceMapper.status(resource),
            utilisation_percent=total_util,
            skills=[ResourceMapper.skill_name(skill) for skill in skills],
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

    async def _resolve_manager_resource_id(self, user: User) -> int:
        manager_resource = await self._resource_repository.find_by_user_id(user.id)
        if manager_resource is None:
            raise ManagerProfileNotFoundError(
                "Manager user does not have an resource profile"
            )
        return manager_resource.id

    @staticmethod
    def _sum_utilisation_by_resource(
        allocations: list[Allocation],
    ) -> dict[int, int]:
        totals: dict[int, int] = defaultdict(int)
        for allocation in allocations:
            totals[allocation.resource_id] += allocation.utilisation_percent
        return dict(totals)

    @staticmethod
    def _availability_label(total_util: int) -> str:
        if total_util >= 100:
            return "FULL"
        return f"{100 - total_util}% free"

    @staticmethod
    def _skill_names(skills: list[ResourceSkill]) -> list[str]:
        return [ResourceMapper.skill_name(skill) for skill in skills]
