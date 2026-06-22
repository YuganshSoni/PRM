from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    subject: str
    body: str


@dataclass(frozen=True)
class SendResult:
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class NotificationIntent:
    notification_type: str
    dedupe_key: str
    to_email: str
    subject: str
    body: str
    entity_type: str | None = None
    entity_id: int | None = None


@dataclass(frozen=True)
class AllocationConfirmationContext:
    resource_name: str
    project_name: str
    from_date: date
    to_date: date
    utilisation_percent: int


@dataclass(frozen=True)
class TimesheetReminderContext:
    resource_name: str
    week_start: date
    reminder_number: int


@dataclass(frozen=True)
class TimesheetFrozenContext:
    resource_name: str
    manager_name: str
    week_start: date


@dataclass(frozen=True)
class ProjectAtRiskContext:
    project_name: str
    manager_name: str
    milestones_summary: str
    health_standing: str
    ai_summary: str
    suggested_help: str
