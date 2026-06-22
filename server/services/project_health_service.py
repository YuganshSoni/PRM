from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from server.core.exceptions import SystemConfigNotFoundError
from server.core.week_utils import WeekCalculator
from server.models.enums import HealthStatus, MilestoneStatus
from server.models.project_health import ProjectHealth
from server.models.project_risk_flag import ProjectRiskFlag
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_health_repository import ProjectHealthRepository
from server.repositories.project_repository import ProjectRepository
from server.repositories.project_risk_flag_repository import ProjectRiskFlagRepository
from server.repositories.system_config_repository import SystemConfigRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.services.scheduler_results import (
    HealthComputationResult,
    HealthFlagResult,
    HealthPersistResult,
    RiskFlagDraft,
)


@dataclass(frozen=True)
class ProjectHealthSnapshot:
    health_status: HealthStatus
    computed_at: datetime


@dataclass(frozen=True)
class RiskFlagView:
    flag_text: str
    is_positive: bool
    sort_order: int


class ProjectHealthService:
    LOW_HOURS_SEVERE_RATIO = Decimal("0.25")
    LOW_HOURS_MODERATE_RATIO = Decimal("0.50")

    def __init__(
        self,
        project_repository: ProjectRepository,
        milestone_repository: MilestoneRepository,
        allocation_repository: AllocationRepository,
        timesheet_repository: TimesheetRepository,
        project_health_repository: ProjectHealthRepository,
        project_risk_flag_repository: ProjectRiskFlagRepository,
        system_config_repository: SystemConfigRepository,
    ) -> None:
        self._project_repository = project_repository
        self._milestone_repository = milestone_repository
        self._allocation_repository = allocation_repository
        self._timesheet_repository = timesheet_repository
        self._project_health_repository = project_health_repository
        self._project_risk_flag_repository = project_risk_flag_repository
        self._system_config_repository = system_config_repository

    async def get_snapshot(self, project_id: int) -> ProjectHealthSnapshot | None:
        health = await self._project_health_repository.find_by_project_id(project_id)
        if health is None:
            return None
        return ProjectHealthSnapshot(
            health_status=HealthStatus(health.health_status),
            computed_at=health.computed_at,
        )

    async def get_risk_flags_for_project(self, project_id: int) -> list[RiskFlagView]:
        health = await self._project_health_repository.find_by_project_id(project_id)
        if health is None:
            return []
        flags = await self._project_risk_flag_repository.find_by_health_id(health.id)
        return [
            RiskFlagView(
                flag_text=flag.flag_text,
                is_positive=flag.is_positive,
                sort_order=flag.sort_order,
            )
            for flag in flags
        ]

    async def get_snapshots_for_projects(
        self, project_ids: list[int]
    ) -> dict[int, ProjectHealthSnapshot]:
        health_rows = await self._project_health_repository.find_by_project_ids(
            project_ids
        )
        return {
            project_id: ProjectHealthSnapshot(
                health_status=HealthStatus(health.health_status),
                computed_at=health.computed_at,
            )
            for project_id, health in health_rows.items()
        }

    async def flag_all_active_projects(self) -> HealthFlagResult:
        projects = await self._project_repository.find_active_projects()
        on_track = attention = at_risk = 0
        at_risk_transitions: list[int] = []

        for project in projects:
            result = await self.compute_and_persist_health(project.id)
            if result.health.health_status == HealthStatus.ON_TRACK:
                on_track += 1
            elif result.health.health_status == HealthStatus.ATTENTION:
                attention += 1
            else:
                at_risk += 1
            if result.transitioned_to_at_risk:
                at_risk_transitions.append(project.id)

        return HealthFlagResult(
            projects_processed=len(projects),
            on_track_count=on_track,
            attention_count=attention,
            at_risk_count=at_risk,
            at_risk_transitions=at_risk_transitions,
        )

    async def compute_and_persist_health(self, project_id: int) -> HealthPersistResult:
        result = await self.compute_health(project_id)
        existing = await self._project_health_repository.find_by_project_id(project_id)
        old_status = (
            HealthStatus(existing.health_status) if existing is not None else None
        )
        now = datetime.now(timezone.utc)

        if existing is None:
            health = ProjectHealth(
                project_id=project_id,
                health_status=result.health_status,
                computed_at=now,
            )
            saved = await self._project_health_repository.save(health)
        else:
            existing.health_status = result.health_status
            existing.computed_at = now
            saved = await self._project_health_repository.save(existing)

        await self._project_risk_flag_repository.delete_by_health_id(saved.id)
        flag_rows = [
            ProjectRiskFlag(
                project_health_id=saved.id,
                flag_text=flag.flag_text,
                is_positive=flag.is_positive,
                sort_order=flag.sort_order,
            )
            for flag in result.risk_flags
        ]
        await self._project_risk_flag_repository.save_all(flag_rows)

        transitioned = (
            old_status != HealthStatus.AT_RISK
            and result.health_status == HealthStatus.AT_RISK
        )
        return HealthPersistResult(health=saved, transitioned_to_at_risk=transitioned)

    async def compute_health(self, project_id: int) -> HealthComputationResult:
        today = date.today()
        prior_week = WeekCalculator.prior_week_monday(today)

        config = await self._system_config_repository.get()
        if config is None:
            raise SystemConfigNotFoundError("System configuration not found")
        max_weekly = Decimal(config.max_weekly_hours)

        milestones = await self._milestone_repository.find_by_project_id(project_id)
        overdue = [
            milestone
            for milestone in milestones
            if milestone.due_date < today
            and milestone.status != MilestoneStatus.DONE
        ]

        allocations = await self._allocation_repository.find_active_for_project_in_week(
            project_id, prior_week
        )
        hours_by_resource = await self._timesheet_repository.sum_hours_by_project_and_week(
            project_id, prior_week
        )

        flags: list[RiskFlagDraft] = []
        sort_order = 0
        severe_low_hours = False
        moderate_low_hours = False

        for milestone in overdue:
            days_overdue = (today - milestone.due_date).days
            flags.append(
                RiskFlagDraft(
                    flag_text=f"{milestone.title} milestone is {days_overdue} days overdue",
                    is_positive=False,
                    sort_order=sort_order,
                )
            )
            sort_order += 1

        for allocation in allocations:
            expected = (
                Decimal(allocation.utilisation_percent) / Decimal(100) * max_weekly
            )
            logged = hours_by_resource.get(allocation.resource_id, Decimal(0))
            resource_name = self._resource_display_name(allocation.resource)

            if expected > 0 and logged < expected * self.LOW_HOURS_SEVERE_RATIO:
                severe_low_hours = True
                flags.append(
                    RiskFlagDraft(
                        flag_text=(
                            f"{resource_name} logged only {logged} hrs last week "
                            f"(expected {expected.quantize(Decimal('0.01'))} hrs)"
                        ),
                        is_positive=False,
                        sort_order=sort_order,
                    )
                )
                sort_order += 1
            elif expected > 0 and logged < expected * self.LOW_HOURS_MODERATE_RATIO:
                moderate_low_hours = True
                flags.append(
                    RiskFlagDraft(
                        flag_text=(
                            f"{resource_name} logged only {logged} hrs last week "
                            f"(expected {expected.quantize(Decimal('0.01'))} hrs)"
                        ),
                        is_positive=False,
                        sort_order=sort_order,
                    )
                )
                sort_order += 1

        if allocations:
            flags.append(
                RiskFlagDraft(
                    flag_text="Resources are correctly allocated",
                    is_positive=True,
                    sort_order=sort_order,
                )
            )

        if overdue and severe_low_hours:
            status = HealthStatus.AT_RISK
        elif overdue or moderate_low_hours or severe_low_hours:
            status = HealthStatus.ATTENTION
        else:
            status = HealthStatus.ON_TRACK

        return HealthComputationResult(health_status=status, risk_flags=flags)

    @staticmethod
    def _resource_display_name(resource: object) -> str:
        user = getattr(resource, "user", None)
        if user is not None:
            return user.full_name
        return "Resource"
