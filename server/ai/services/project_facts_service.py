from datetime import date

from server.ai.dto.project_facts import (
    ProjectFactsAllocation,
    ProjectFactsDTO,
    ProjectFactsMilestone,
)
from server.core.exceptions import ProjectNotFoundError
from server.models.enums import MilestoneStatus
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.services.project_health_service import ProjectHealthService


class ProjectFactsService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        milestone_repository: MilestoneRepository,
        allocation_repository: AllocationRepository,
        project_health_service: ProjectHealthService,
    ) -> None:
        self._project_repository = project_repository
        self._milestone_repository = milestone_repository
        self._allocation_repository = allocation_repository
        self._project_health_service = project_health_service

    async def collect(
        self, project_id: int, manager_resource_id: int
    ) -> ProjectFactsDTO:
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

        milestone_rows = [
            ProjectFactsMilestone(
                title=milestone.title,
                due_date=milestone.due_date.isoformat(),
                status=str(milestone.status),
                is_overdue=(
                    milestone.due_date < today
                    and MilestoneStatus(milestone.status) != MilestoneStatus.DONE
                ),
            )
            for milestone in milestones
        ]

        allocation_rows = []
        for allocation in allocations:
            user = getattr(allocation.resource, "user", None)
            name = user.full_name if user is not None else "Resource"
            allocation_rows.append(
                ProjectFactsAllocation(
                    resource_name=name,
                    utilisation_percent=allocation.utilisation_percent,
                )
            )

        hours_notes = [
            flag.flag_text
            for flag in risk_flags
            if not flag.is_positive and "logged only" in flag.flag_text.lower()
        ]

        return ProjectFactsDTO(
            project_id=project.id,
            project_name=project.name,
            project_status=str(project.status),
            end_date=project.end_date.isoformat(),
            health_status=snapshot.health_status.value if snapshot else None,
            milestones=milestone_rows,
            allocations=allocation_rows,
            risk_flags=[flag.flag_text for flag in risk_flags if not flag.is_positive],
            hours_notes=hours_notes,
        )
