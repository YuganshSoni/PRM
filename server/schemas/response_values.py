from enum import StrEnum


class ApiStatus(StrEnum):
    OK = "ok"


class DatabaseConnectionStatus(StrEnum):
    CONNECTED = "connected"


class ErrorCode(StrEnum):
    INTERNAL_SERVER_ERROR = "InternalServerError"


class TokenType(StrEnum):
    BEARER = "bearer"


class AuthMessage(StrEnum):
    LOGOUT_SUCCESS = "Logged out successfully"
    PASSWORD_UPDATED = "Password updated successfully"


class UserMessage(StrEnum):
    ACCOUNT_CREATED = (
        "Account created. User must change password on first login."
    )
    PASSWORD_RESET = (
        "Password reset. User will be prompted to change it on next login."
    )
    USER_DEACTIVATED = "User deactivated."
    USER_REACTIVATED = "Account reactivated."


class EmployeeMessage(StrEnum):
    PROFILE_CREATED = "Resource profile created (BENCH)."
    PROFILE_UPDATED = "Resource profile updated."
    MANAGER_ASSIGNED = "Manager assigned successfully."
    EMPLOYEE_DEACTIVATED = "Resource deactivated."


class SkillMessage(StrEnum):
    SKILL_ADDED = "Skill added."
    SKILL_UPDATED = "Proficiency updated."
    SKILL_REMOVED = "Skill removed."


class ProjectMessage(StrEnum):
    PROJECT_CREATED = "Project created."
    PROJECT_UPDATED = "Project updated."


class MilestoneMessage(StrEnum):
    MILESTONE_ADDED = "Milestone added."
    MILESTONE_UPDATED = "Milestone updated."


class ConfigMessage(StrEnum):
    SETTINGS_UPDATED = "Settings updated."


class AllocationMessage(StrEnum):
    ALLOCATION_CREATED = "Allocation saved."
    ALLOCATION_ENDED = "Allocation ended."


class TimesheetMessage(StrEnum):
    TIMESHEET_SUBMITTED = "Timesheet submitted successfully."
