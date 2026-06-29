from datetime import date

from server.notifications.dto.notification_dto import (
    AllocationConfirmationContext,
    ProjectAtRiskContext,
    TimesheetFrozenContext,
    TimesheetReminderContext,
)
from server.notifications.templates.email_templates import EmailTemplateRenderer


def test_allocation_confirmation_template():
    subject, body = EmailTemplateRenderer.allocation_confirmation(
        AllocationConfirmationContext(
            resource_name="Ada Lovelace",
            project_name="Analytical Engine",
            from_date=date(2026, 1, 1),
            to_date=date(2026, 3, 31),
            utilisation_percent=75,
        )
    )

    assert subject == "Project Allocation: Analytical Engine"
    assert "Hello Ada Lovelace" in body
    assert "Analytical Engine" in body
    assert "2026-01-01" in body
    assert "2026-03-31" in body
    assert "75% utilization" in body


def test_timesheet_reminder_template():
    subject, body = EmailTemplateRenderer.timesheet_reminder(
        TimesheetReminderContext(
            resource_name="Grace Hopper",
            week_start=date(2026, 7, 6),
            reminder_number=2,
        )
    )

    assert subject == "Timesheet Reminder 2: week 2026-07-06"
    assert "Hello Grace Hopper" in body
    assert "week starting 2026-07-06" in body
    assert "has not been submitted" in body


def test_timesheet_frozen_employee_template():
    subject, body = EmailTemplateRenderer.timesheet_frozen_employee(
        TimesheetFrozenContext(
            resource_name="Alan Turing",
            manager_name="Joan Clarke",
            week_start=date(2026, 7, 6),
        )
    )

    assert subject == "Timesheet submission access frozen"
    assert "Hello Alan Turing" in body
    assert "week 2026-07-06" in body
    assert "Contact your manager (Joan Clarke)" in body


def test_timesheet_frozen_manager_template():
    subject, body = EmailTemplateRenderer.timesheet_frozen_manager(
        TimesheetFrozenContext(
            resource_name="Alan Turing",
            manager_name="Joan Clarke",
            week_start=date(2026, 7, 6),
        )
    )

    assert subject == "Employee timesheet frozen: Alan Turing"
    assert "Hello Joan Clarke" in body
    assert "Alan Turing has not submitted" in body
    assert "week 2026-07-06" in body
    assert "submission access is now frozen" in body


def test_project_at_risk_template():
    subject, body = EmailTemplateRenderer.project_at_risk(
        ProjectAtRiskContext(
            project_name="Apollo",
            manager_name="Gene Kranz",
            milestones_summary="- Launch delayed",
            health_standing="Red",
            ai_summary="Critical path slipped.",
            suggested_help="- Jane Doe: Python (ADVANCED)",
        )
    )

    assert subject == "Project At Risk: Apollo"
    assert "Hello Gene Kranz" in body
    assert "Project: Apollo" in body
    assert "Health standing: Red" in body
    assert "Milestones:\n- Launch delayed" in body
    assert "AI Risk Summary:\nCritical path slipped." in body
    assert "Suggested Help:\n- Jane Doe: Python (ADVANCED)" in body
