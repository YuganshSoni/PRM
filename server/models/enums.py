from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EmployeeStatus(StrEnum):
    BENCH = "BENCH"
    ALLOCATED = "ALLOCATED"


class SkillCategory(StrEnum):
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    DEVOPS = "DEVOPS"
    QA = "QA"
    OTHER = "OTHER"


class ProficiencyLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class ProjectStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"


class MilestoneStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class TimesheetStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    MISSED = "MISSED"


class HealthStatus(StrEnum):
    ON_TRACK = "ON_TRACK"
    ATTENTION = "ATTENTION"
    AT_RISK = "AT_RISK"


class LlmProvider(StrEnum):
    GEMINI = "GEMINI"
    GROQ = "GROQ"
