from server.notifications.dto.notification_dto import (
    AllocationConfirmationContext,
    ProjectAtRiskContext,
    TimesheetFrozenContext,
    TimesheetReminderContext,
)


class EmailTemplateRenderer:
    @staticmethod
    def allocation_confirmation(ctx: AllocationConfirmationContext) -> tuple[str, str]:
        subject = f"Project Allocation: {ctx.project_name}"
        body = (
            f"Hello {ctx.resource_name}, you have been allocated to the project "
            f"{ctx.project_name} from {ctx.from_date.isoformat()} to "
            f"{ctx.to_date.isoformat()} with {ctx.utilisation_percent}% utilization."
        )
        return subject, body

    @staticmethod
    def timesheet_reminder(ctx: TimesheetReminderContext) -> tuple[str, str]:
        subject = f"Timesheet Reminder {ctx.reminder_number}: week {ctx.week_start}"
        body = (
            f"Hello {ctx.resource_name}, your timesheet for week starting "
            f"{ctx.week_start.isoformat()} has not been submitted. "
            f"Please submit it as soon as possible."
        )
        return subject, body

    @staticmethod
    def timesheet_frozen_employee(ctx: TimesheetFrozenContext) -> tuple[str, str]:
        subject = "Timesheet submission access frozen"
        body = (
            f"Hello {ctx.resource_name}, your timesheet submission access has been "
            f"frozen for week {ctx.week_start.isoformat()} due to non-submission. "
            f"Contact your manager ({ctx.manager_name}) to restore access."
        )
        return subject, body

    @staticmethod
    def timesheet_frozen_manager(ctx: TimesheetFrozenContext) -> tuple[str, str]:
        subject = f"Employee timesheet frozen: {ctx.resource_name}"
        body = (
            f"Hello {ctx.manager_name}, {ctx.resource_name} has not submitted the "
            f"timesheet for week {ctx.week_start.isoformat()}. Their submission "
            f"access is now frozen. Please review and restore access when ready."
        )
        return subject, body

    @staticmethod
    def project_at_risk(ctx: ProjectAtRiskContext) -> tuple[str, str]:
        subject = f"Project At Risk: {ctx.project_name}"
        body = (
            f"Hello {ctx.manager_name},\n\n"
            f"Project: {ctx.project_name}\n"
            f"Health standing: {ctx.health_standing}\n\n"
            f"Milestones:\n{ctx.milestones_summary}\n\n"
            f"AI Risk Summary:\n{ctx.ai_summary}\n\n"
            f"Suggested Help:\n{ctx.suggested_help}\n"
        )
        return subject, body
