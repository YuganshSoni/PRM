from datetime import date

from server.core.exceptions import PrmError
from server.models.enums import (
    ProficiencyLevel,
    ProjectStatus,
    ResourceStatusEnum,
    SkillCategoryEnum,
    UserRole,
)
from server.schemas.response_values import (
    ApiStatus,
    AuthMessage,
    DatabaseConnectionStatus,
    ErrorCode,
    TokenType,
)
from server.schemas.responses.ai import (
    RiskSummaryResponse,
    SkillMatchCandidateResponse,
    SkillMatchResponse,
    TeamBuildResponse,
    TeamRoleGapResponse,
    TeamRoleMatchResponse,
    ParsedTeamRoleResponse,
)
from server.schemas.responses.auth import (
    ChangePasswordResponse,
    CurrentUserResponse,
    LoginResponse,
    LogoutResponse,
)
from server.schemas.responses.error import ErrorResponse
from server.schemas.responses.health import HealthDatabaseResponse, HealthStatusResponse
from server.schemas.responses.project import (
    ProjectCreatedResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSummaryResponse,
)
from server.schemas.responses.resource import (
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeSummaryResponse,
)
from server.schemas.response_values import ProjectMessage


def test_auth_response_schemas():
    login = LoginResponse(
        access_token="tok",
        token_type=TokenType.BEARER,
        role=UserRole.MANAGER,
        force_password_change=False,
        full_name="Ada",
    )
    change = ChangePasswordResponse(
        access_token="tok2",
        token_type=TokenType.BEARER,
        role=UserRole.MANAGER,
        force_password_change=False,
        message=AuthMessage.PASSWORD_UPDATED,
    )
    logout = LogoutResponse(message=AuthMessage.LOGOUT_SUCCESS)
    me = CurrentUserResponse(
        id=1,
        username="ada",
        role=UserRole.MANAGER,
        force_password_change=False,
    )
    assert login.role == UserRole.MANAGER
    assert change.message == AuthMessage.PASSWORD_UPDATED
    assert logout.message == AuthMessage.LOGOUT_SUCCESS
    assert me.username == "ada"


def test_ai_response_schemas():
    skill = SkillMatchResponse(
        items=[
            SkillMatchCandidateResponse(
                resource_id=1,
                resource_name="Ada",
                reason="Fit",
                free_hours_per_week=10.0,
                suggested_utilisation_percent=25,
                rank=1,
            )
        ],
        message=None,
        llm_invoked=True,
        weekly_hours_requested=20,
        requirement_parse_invoked=True,
        parsed_summary="Need Python",
    )
    risk = RiskSummaryResponse(
        project_id=1,
        project_name="Apollo",
        summary="At risk due to overdue milestones.",
        llm_invoked=True,
    )
    team = TeamBuildResponse(
        project_id=1,
        parsed_roles=[
            ParsedTeamRoleResponse(
                role_key="r1",
                role_title="Backend",
                skill_names=["Python"],
                skill_category=SkillCategoryEnum.BACKEND,
                min_proficiency=ProficiencyLevel.INTERMEDIATE,
            )
        ],
        matches=[
            TeamRoleMatchResponse(
                role_key="r1",
                role_title="Backend",
                resource_id=1,
                resource_name="Ada",
                reason="Strong match",
                match_score=90,
            )
        ],
        gaps=[
            TeamRoleGapResponse(
                role_key="r2",
                role_title="QA",
                gap_type="SKILL_ABSENCE",
                message="No QA on bench",
                available_from=None,
                candidate_hint_name=None,
            )
        ],
        llm_invoked=True,
    )
    assert skill.llm_invoked is True
    assert "AI-generated" in risk.disclaimer
    assert team.project_id == 1


def test_error_and_health_responses():
    err = ErrorResponse.from_prm_error(PrmError("boom", code="SampleError"))
    assert err.detail == "boom"
    assert err.code == "SampleError"
    internal = ErrorResponse.internal_server_error()
    assert internal.code == ErrorCode.INTERNAL_SERVER_ERROR

    health = HealthStatusResponse(status=ApiStatus.OK)
    db = HealthDatabaseResponse(
        status=ApiStatus.OK,
        database=DatabaseConnectionStatus.CONNECTED,
    )
    assert health.status == ApiStatus.OK
    assert db.database == DatabaseConnectionStatus.CONNECTED


def test_project_and_resource_responses():
    summary = ProjectSummaryResponse(
        id=1,
        name="Apollo",
        manager_name="Ada",
        end_date=date(2026, 6, 1),
        status=ProjectStatus.ACTIVE,
        story_points_done=5,
        story_points_total=10,
    )
    detail = ProjectDetailResponse(
        id=1,
        name="Apollo",
        description=None,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        status=ProjectStatus.ACTIVE,
        manager_id=2,
        manager_name="Ada",
        total_story_points=10,
    )
    listing = ProjectListResponse(items=[summary], total=1, limit=10, offset=0)
    created = ProjectCreatedResponse(
        id=1,
        name="Apollo",
        status=ProjectStatus.PLANNED,
        message=ProjectMessage.PROJECT_CREATED,
    )
    emp = EmployeeSummaryResponse(
        id=1,
        full_name="Ada",
        department="Eng",
        status=ResourceStatusEnum.BENCH,
        is_active=True,
    )
    emp_detail = EmployeeDetailResponse(
        id=1,
        user_id=9,
        full_name="Ada",
        email="ada@example.com",
        department="Eng",
        designation="Dev",
        status=ResourceStatusEnum.BENCH,
        is_active=True,
        manager_id=None,
        active_allocations=[],
    )
    emp_list = EmployeeListResponse(
        items=[emp],
        total=1,
        bench_count=1,
        allocated_count=0,
        limit=10,
        offset=0,
    )
    assert listing.total == 1
    assert created.id == 1
    assert emp_detail.email == "ada@example.com"
    assert emp_list.bench_count == 1
    assert detail.manager_id == 2
