import logging
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.core.exceptions import (
    AccountInactiveError,
    AllocationNotFoundError,
    ConflictError,
    DatabaseUnavailableError,
    DuplicateEmailError,
    DuplicateSkillError,
    DuplicateTimesheetError,
    DuplicateUsernameError,
    EmployeeAlreadyInactiveError,
    EmployeeProfileNotFoundError,
    EmployeeNotAllocatableError,
    EmployeeNotFoundError,
    ForbiddenError,
    FutureWeekError,
    HoursExceededError,
    InvalidActivityTagError,
    InvalidCredentialsError,
    InvalidWeekStartError,
    InvalidManagerRoleError,
    InvalidLlmApiKeyError,
    InvalidMaxWeeklyHoursError,
    InvalidAllocationDatesError,
    InvalidProjectDatesError,
    InvalidProjectManagerError,
    InvalidProjectStatusError,
    InvalidProjectStatusForAllocationError,
    InvalidSchedulerIntervalError,
    InvalidSmtpConfigError,
    InvalidSmtpPortError,
    InvalidSkillCategoryEnumError,
    InvalidStoryPointsError,
    NoConfigFieldsToUpdateError,
    NoTimesheetEntriesError,
    NotAllocatedToProjectError,
    NotProjectOwnerError,
    OtherTagRequiresLabelError,
    OverAllocationError,
    InvalidSkillMatchRequestError,
    InvalidTeamBuildRequestError,
    TimesheetSubmissionFrozenError,
    ComplianceRecordNotFoundError,
    BulkAllocationValidationError,
    InvalidTokenError,
    InvalidUserRoleForEmployeeError,
    LlmNotConfiguredError,
    LlmInvocationError,
    ManagerProfileNotFoundError,
    ManagerUserNotFoundError,
    MilestoneNotFoundError,
    NotFoundError,
    ProjectNotFoundError,
    PasswordMismatchError,
    PrmError,
    SelfManagerAssignmentError,
    SelfOperationForbiddenError,
    SkillNotFoundError,
    SystemConfigNotFoundError,
    ResourceStatusNotFoundError,
    TimesheetNotFoundError,
    TokenExpiredError,
    TotalHoursExceededError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
    ValidationError,
    WeakPasswordError,
)
from server.schemas.responses.error import ErrorResponse

logger = logging.getLogger(__name__)


class ExceptionHandlerRegistrar:
    STATUS_MAP: ClassVar[dict[type[PrmError], int]] = {
        WeakPasswordError: 400,
        PasswordMismatchError: 400,
        ValidationError: 400,
        UserAlreadyInactiveError: 400,
        UserAlreadyActiveError: 400,
        SelfOperationForbiddenError: 400,
        InvalidUserRoleForEmployeeError: 400,
        EmployeeAlreadyInactiveError: 400,
        InvalidManagerRoleError: 400,
        SelfManagerAssignmentError: 400,
        InvalidSkillCategoryEnumError: 400,
        InvalidProjectManagerError: 400,
        InvalidProjectDatesError: 400,
        InvalidProjectStatusError: 400,
        InvalidStoryPointsError: 400,
        InvalidSchedulerIntervalError: 400,
        InvalidMaxWeeklyHoursError: 400,
        InvalidSmtpPortError: 400,
        InvalidSmtpConfigError: 400,
        InvalidLlmApiKeyError: 400,
        NoConfigFieldsToUpdateError: 400,
        OverAllocationError: 400,
        InvalidAllocationDatesError: 400,
        InvalidProjectStatusForAllocationError: 400,
        EmployeeNotAllocatableError: 400,
        FutureWeekError: 400,
        InvalidWeekStartError: 400,
        HoursExceededError: 400,
        TotalHoursExceededError: 400,
        NotAllocatedToProjectError: 400,
        InvalidActivityTagError: 400,
        OtherTagRequiresLabelError: 400,
        NoTimesheetEntriesError: 400,
        InvalidSkillMatchRequestError: 400,
        InvalidTeamBuildRequestError: 400,
        TimesheetSubmissionFrozenError: 400,
        ComplianceRecordNotFoundError: 404,
        BulkAllocationValidationError: 400,
        InvalidCredentialsError: 401,
        AccountInactiveError: 401,
        InvalidTokenError: 401,
        TokenExpiredError: 401,
        ForbiddenError: 403,
        NotProjectOwnerError: 403,
        UserNotFoundError: 404,
        AllocationNotFoundError: 404,
        EmployeeNotFoundError: 404,
        ManagerUserNotFoundError: 404,
        ManagerProfileNotFoundError: 404,
        EmployeeProfileNotFoundError: 404,
        TimesheetNotFoundError: 404,
        SkillNotFoundError: 404,
        ProjectNotFoundError: 404,
        MilestoneNotFoundError: 404,
        SystemConfigNotFoundError: 404,
        ResourceStatusNotFoundError: 500,
        NotFoundError: 404,
        ConflictError: 409,
        DuplicateUsernameError: 409,
        DuplicateEmailError: 409,
        DuplicateSkillError: 409,
        DuplicateTimesheetError: 409,
        DatabaseUnavailableError: 503,
        LlmNotConfiguredError: 503,
        LlmInvocationError: 502,
    }

    def register(self, app: FastAPI) -> None:
        app.add_exception_handler(PrmError, self.handle_prm_error)
        app.add_exception_handler(Exception, self.handle_unhandled)

    def status_for(self, exc: PrmError) -> int:
        for exc_type, status in self.STATUS_MAP.items():
            if isinstance(exc, exc_type):
                return status
        return 500

    async def handle_prm_error(
        self, _request: Request, exc: PrmError
    ) -> JSONResponse:
        if isinstance(exc, LlmInvocationError):
            logger.error("LLM invocation error returned to client: %s", exc)
        body = ErrorResponse.from_prm_error(exc)
        return JSONResponse(
            status_code=self.status_for(exc),
            content=body.model_dump(),
        )

    async def handle_unhandled(
        self, _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc)
        body = ErrorResponse.internal_server_error()
        return JSONResponse(status_code=500, content=body.model_dump())
