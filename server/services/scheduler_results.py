from dataclasses import dataclass
from typing import TYPE_CHECKING

from server.models.enums import HealthStatus

if TYPE_CHECKING:
    from server.models.project_health import ProjectHealth


@dataclass(frozen=True)
class RecomputeResult:
    bench_count: int
    allocated_count: int


@dataclass(frozen=True)
class MissedMarkResult:
    created: int
    updated: int
    skipped: int


@dataclass(frozen=True)
class RiskFlagDraft:
    flag_text: str
    is_positive: bool
    sort_order: int


@dataclass(frozen=True)
class HealthComputationResult:
    health_status: HealthStatus
    risk_flags: list[RiskFlagDraft]


@dataclass(frozen=True)
class HealthPersistResult:
    health: "ProjectHealth"
    transitioned_to_at_risk: bool


@dataclass(frozen=True)
class HealthFlagResult:
    projects_processed: int
    on_track_count: int
    attention_count: int
    at_risk_count: int
    at_risk_transitions: list[int]


@dataclass(frozen=True)
class ComplianceRunResult:
    reminders_sent: int
    freezes_applied: int


@dataclass(frozen=True)
class SchedulerRunResult:
    recompute: RecomputeResult
    missed: MissedMarkResult
    health: HealthFlagResult
    compliance: ComplianceRunResult | None = None
    at_risk_emails_sent: int = 0
