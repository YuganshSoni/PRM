from dataclasses import dataclass
from datetime import date, datetime, timezone

from server.core.exceptions import (
    ComplianceRecordNotFoundError,
    EmployeeNotAllocatableError,
    ManagerProfileNotFoundError,
)
from server.core.working_day_calendar import WorkingDayCalendar
from server.core.week_utils import WeekCalculator
from server.models.enums import NotificationType, TimesheetComplianceStatus, TimesheetStatus
from server.models.timesheet_compliance_record import TimesheetComplianceRecord
from server.models.user import User
from server.notifications.dto.notification_dto import (
    NotificationIntent,
    TimesheetFrozenContext,
    TimesheetReminderContext,
)
from server.notifications.services.notification_service import NotificationService
from server.notifications.templates.email_templates import EmailTemplateRenderer
from server.repositories.allocation_repository import AllocationRepository
from server.repositories.resource_repository import ResourceRepository
from server.repositories.timesheet_compliance_repository import TimesheetComplianceRepository
from server.repositories.timesheet_repository import TimesheetRepository
from server.schemas.responses.timesheet_compliance import TeamComplianceRowResponse
from server.services.resource_mapper import ResourceMapper
from server.services.scheduler_results import ComplianceRunResult


class TimesheetComplianceService:
    def __init__(
        self,
        compliance_repository: TimesheetComplianceRepository,
        timesheet_repository: TimesheetRepository,
        allocation_repository: AllocationRepository,
        resource_repository: ResourceRepository,
        notification_service: NotificationService,
    ) -> None:
        self._compliance_repository = compliance_repository
        self._timesheet_repository = timesheet_repository
        self._allocation_repository = allocation_repository
        self._resource_repository = resource_repository
        self._notification_service = notification_service

    async def is_submission_frozen(self, resource_id: int) -> bool:
        record = await self._compliance_repository.find_frozen_by_resource(
            resource_id
        )
        return record is not None

    async def run_daily(self, today: date | None = None) -> ComplianceRunResult:
        today = today or date.today()
        reminders = freezes = 0
        week_start = WeekCalculator.prior_week_monday(today)

        allocations = await self._allocation_repository.find_overlapping_week(
            week_start
        )
        resource_ids = {item.resource_id for item in allocations}

        for resource_id in resource_ids:
            resource = await self._resource_repository.get_by_id_with_user(
                resource_id
            )
            if resource is None or not resource.is_active:
                continue

            timesheet = await self._timesheet_repository.find_by_resource_and_week(
                resource_id, week_start
            )
            if timesheet is not None and timesheet.status == TimesheetStatus.SUBMITTED:
                continue

            record = await self._get_or_create_record(resource_id, week_start)
            if record.status in (
                TimesheetComplianceStatus.SUBMITTED,
                TimesheetComplianceStatus.RESTORED,
            ):
                continue

            resource_name = ResourceMapper.full_name(resource)
            resource_email = resource.user.email if resource.user else ""
            manager_email = await self._manager_email(resource.manager_id)

            if today == WorkingDayCalendar.reminder_1_day(week_start):
                if record.status == TimesheetComplianceStatus.PENDING:
                    subject, body = EmailTemplateRenderer.timesheet_reminder(
                        TimesheetReminderContext(
                            resource_name=resource_name,
                            week_start=week_start,
                            reminder_number=1,
                        )
                    )
                    await self._notification_service.send(
                        NotificationIntent(
                            notification_type=NotificationType.TIMESHEET_REMINDER_1,
                            dedupe_key=f"timesheet:{resource_id}:{week_start}:r1",
                            to_email=resource_email,
                            subject=subject,
                            body=body,
                            entity_type="resource",
                            entity_id=resource_id,
                        )
                    )
                    record.status = TimesheetComplianceStatus.REMINDER_1_SENT
                    record.reminder_1_sent_at = datetime.now(timezone.utc)
                    await self._compliance_repository.save(record)
                    reminders += 1

            elif today == WorkingDayCalendar.reminder_2_day(week_start):
                if record.status == TimesheetComplianceStatus.REMINDER_1_SENT:
                    subject, body = EmailTemplateRenderer.timesheet_reminder(
                        TimesheetReminderContext(
                            resource_name=resource_name,
                            week_start=week_start,
                            reminder_number=2,
                        )
                    )
                    await self._notification_service.send(
                        NotificationIntent(
                            notification_type=NotificationType.TIMESHEET_REMINDER_2,
                            dedupe_key=f"timesheet:{resource_id}:{week_start}:r2",
                            to_email=resource_email,
                            subject=subject,
                            body=body,
                            entity_type="resource",
                            entity_id=resource_id,
                        )
                    )
                    record.status = TimesheetComplianceStatus.REMINDER_2_SENT
                    record.reminder_2_sent_at = datetime.now(timezone.utc)
                    await self._compliance_repository.save(record)
                    reminders += 1

            elif today >= WorkingDayCalendar.freeze_day(week_start):
                if record.status in (
                    TimesheetComplianceStatus.PENDING,
                    TimesheetComplianceStatus.REMINDER_1_SENT,
                    TimesheetComplianceStatus.REMINDER_2_SENT,
                ):
                    manager_name = await self._manager_name(resource.manager_id)
                    frozen_ctx = TimesheetFrozenContext(
                        resource_name=resource_name,
                        manager_name=manager_name,
                        week_start=week_start,
                    )
                    emp_subject, emp_body = EmailTemplateRenderer.timesheet_frozen_employee(
                        frozen_ctx
                    )
                    mgr_subject, mgr_body = EmailTemplateRenderer.timesheet_frozen_manager(
                        frozen_ctx
                    )
                    await self._notification_service.send(
                        NotificationIntent(
                            notification_type=NotificationType.TIMESHEET_FROZEN_EMPLOYEE,
                            dedupe_key=f"timesheet:{resource_id}:{week_start}:frozen_emp",
                            to_email=resource_email,
                            subject=emp_subject,
                            body=emp_body,
                            entity_type="resource",
                            entity_id=resource_id,
                        )
                    )
                    await self._notification_service.send(
                        NotificationIntent(
                            notification_type=NotificationType.TIMESHEET_FROZEN_MANAGER,
                            dedupe_key=f"timesheet:{resource_id}:{week_start}:frozen_mgr",
                            to_email=manager_email,
                            subject=mgr_subject,
                            body=mgr_body,
                            entity_type="resource",
                            entity_id=resource_id,
                        )
                    )
                    record.status = TimesheetComplianceStatus.FROZEN
                    record.frozen_at = datetime.now(timezone.utc)
                    await self._compliance_repository.save(record)
                    freezes += 1

        return ComplianceRunResult(reminders_sent=reminders, freezes_applied=freezes)

    async def restore_access(
        self, user: User, resource_id: int, week_start: date
    ) -> TimesheetComplianceRecord:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        resource = await self._resource_repository.get_by_id_with_user(resource_id)
        if resource is None or resource.manager_id != manager_resource_id:
            raise EmployeeNotAllocatableError("Resource not in your team")

        record = await self._compliance_repository.find_by_resource_and_week(
            resource_id, week_start
        )
        if record is None or record.status != TimesheetComplianceStatus.FROZEN:
            raise ComplianceRecordNotFoundError(
                "No frozen compliance record found for this week"
            )

        record.status = TimesheetComplianceStatus.RESTORED
        record.restored_at = datetime.now(timezone.utc)
        record.restored_by_manager_id = manager_resource_id
        return await self._compliance_repository.save(record)

    async def list_team_compliance_rows(
        self, user: User
    ) -> list[TeamComplianceRowResponse]:
        records = await self.list_team_compliance(user)
        rows: list[TeamComplianceRowResponse] = []
        for record in records:
            resource = await self._resource_repository.get_by_id_with_user(
                record.resource_id
            )
            rows.append(
                TeamComplianceRowResponse(
                    resource_id=record.resource_id,
                    resource_name=ResourceMapper.full_name(resource)
                    if resource
                    else "Resource",
                    week_start=record.week_start,
                    status=record.status,
                    frozen_at=record.frozen_at.date() if record.frozen_at else None,
                )
            )
        return rows

    async def list_team_compliance(
        self, user: User
    ) -> list[TimesheetComplianceRecord]:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        return await self._compliance_repository.find_frozen_for_manager(
            manager_resource_id
        )

    async def mark_submitted(self, resource_id: int, week_start: date) -> None:
        record = await self._compliance_repository.find_by_resource_and_week(
            resource_id, week_start
        )
        if record is not None:
            record.status = TimesheetComplianceStatus.SUBMITTED
            await self._compliance_repository.save(record)

    async def _get_or_create_record(
        self, resource_id: int, week_start: date
    ) -> TimesheetComplianceRecord:
        existing = await self._compliance_repository.find_by_resource_and_week(
            resource_id, week_start
        )
        if existing is not None:
            return existing
        record = TimesheetComplianceRecord(
            resource_id=resource_id,
            week_start=week_start,
            status=TimesheetComplianceStatus.PENDING,
        )
        return await self._compliance_repository.save(record)

    async def _manager_email(self, manager_id: int | None) -> str:
        if manager_id is None:
            return ""
        manager = await self._resource_repository.get_by_id_with_user(manager_id)
        if manager is None or manager.user is None:
            return ""
        return manager.user.email

    async def _manager_name(self, manager_id: int | None) -> str:
        if manager_id is None:
            return "Manager"
        manager = await self._resource_repository.get_by_id_with_user(manager_id)
        if manager is None:
            return "Manager"
        return ResourceMapper.full_name(manager)

    async def _resolve_manager_resource_id(self, user: User) -> int:
        resource = await self._resource_repository.find_by_user_id(user.id)
        if resource is None:
            raise ManagerProfileNotFoundError("Manager profile not found")
        return resource.id
