class PrmError(Exception):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).__name__


class NotFoundError(PrmError):
    pass


class ConflictError(PrmError):
    pass


class ValidationError(PrmError):
    pass


class DatabaseUnavailableError(PrmError):
    pass


class WeakPasswordError(PrmError):
    pass


class PasswordMismatchError(PrmError):
    pass


class InvalidCredentialsError(PrmError):
    pass


class AccountInactiveError(PrmError):
    pass


class InvalidTokenError(PrmError):
    pass


class TokenExpiredError(PrmError):
    pass


class ForbiddenError(PrmError):
    pass


class UserNotFoundError(PrmError):
    pass


class DuplicateUsernameError(ConflictError):
    pass


class DuplicateEmailError(ConflictError):
    pass


class UserAlreadyInactiveError(ValidationError):
    pass


class UserAlreadyActiveError(ValidationError):
    pass


class SelfOperationForbiddenError(ValidationError):
    pass


class EmployeeNotFoundError(NotFoundError):
    pass


class InvalidUserRoleForEmployeeError(ValidationError):
    pass


class EmployeeAlreadyInactiveError(ValidationError):
    pass


class ManagerUserNotFoundError(NotFoundError):
    pass


class InvalidManagerRoleError(ValidationError):
    pass


class ManagerProfileNotFoundError(NotFoundError):
    pass


class SelfManagerAssignmentError(ValidationError):
    pass


class DuplicateSkillError(ConflictError):
    pass


class SkillNotFoundError(NotFoundError):
    pass


class InvalidSkillCategoryError(ValidationError):
    pass


class ProjectNotFoundError(NotFoundError):
    pass


class MilestoneNotFoundError(NotFoundError):
    pass


class InvalidProjectManagerError(ValidationError):
    pass


class InvalidProjectDatesError(ValidationError):
    pass


class InvalidProjectStatusError(ValidationError):
    pass


class InvalidStoryPointsError(ValidationError):
    pass


class SystemConfigNotFoundError(NotFoundError):
    pass


class InvalidSchedulerIntervalError(ValidationError):
    pass


class InvalidMaxWeeklyHoursError(ValidationError):
    pass


class InvalidLlmApiKeyError(ValidationError):
    pass


class NoConfigFieldsToUpdateError(ValidationError):
    pass
