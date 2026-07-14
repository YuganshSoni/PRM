from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from server.models.enums import (
    LlmProvider,
    MilestoneStatus,
    ProficiencyLevel,
    ProjectStatus,
    SkillCategoryEnum,
    UserRole,
)
from server.schemas.requests.allocation import (
    BulkCreateAllocationRequest,
    CreateAllocationRequest,
)
from server.schemas.requests.ai import SkillMatchRequest, TeamBuildRequest
from server.schemas.requests.auth import ChangePasswordRequest, LoginRequest
from server.schemas.requests.config import UpdateSystemConfigRequest
from server.schemas.requests.milestone import (
    AddMilestoneRequest,
    UpdateMilestoneStatusRequest,
)
from server.schemas.requests.project import CreateProjectRequest, UpdateProjectRequest
from server.schemas.requests.resource import AssignManagerRequest, UpdateEmployeeRequest
from server.schemas.requests.skill import AddSkillRequest, UpdateSkillProficiencyRequest
from server.schemas.requests.timesheet import SubmitTimesheetRequest
from server.schemas.requests.timesheet_compliance import RestoreTimesheetComplianceRequest
from server.schemas.requests.user import CreateUserRequest, ResetPasswordRequest


def test_login_request_strips_username():
    req = LoginRequest(username="  alice  ", password="Secret1!")
    assert req.username == "alice"


def test_change_password_request():
    req = ChangePasswordRequest(new_password="NewPass1!", confirm_password="NewPass1!")
    assert req.new_password == "NewPass1!"


def test_skill_match_request_min_length():
    with pytest.raises(ValidationError):
        SkillMatchRequest(requirement="too short")
    req = SkillMatchRequest(requirement="Need a React engineer for staffing")
    assert req.project_id is None


def test_team_build_request_requires_project_id():
    req = TeamBuildRequest(
        requirement="Need backend and frontend pair",
        project_id=5,
    )
    assert req.project_id == 5


def test_create_project_request():
    req = CreateProjectRequest(
        name="Apollo",
        description=None,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        status=ProjectStatus.PLANNED,
        manager_id=1,
        total_story_points=10,
    )
    assert req.name == "Apollo"


def test_update_project_request():
    req = UpdateProjectRequest(
        name="Apollo",
        description="x",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        status=ProjectStatus.ACTIVE,
        manager_id=2,
        total_story_points=20,
    )
    assert req.status == ProjectStatus.ACTIVE


def test_create_user_and_reset_password_requests():
    create = CreateUserRequest(
        full_name="Ada Lovelace",
        email="ada@example.com",
        username="ada",
        temporary_password="Temp1!",
        role=UserRole.RESOURCE,
    )
    reset = ResetPasswordRequest(temporary_password="Temp2!")
    assert create.role == UserRole.RESOURCE
    assert reset.temporary_password == "Temp2!"


def test_resource_requests():
    update = UpdateEmployeeRequest(
        full_name="Ada",
        email="ada@example.com",
        department="Eng",
        designation="Dev",
    )
    assign = AssignManagerRequest(resource_user_id=1, manager_user_id=2)
    assert update.department == "Eng"
    assert assign.manager_user_id == 2


def test_allocation_requests_and_bulk_unique_validation():
    CreateAllocationRequest(
        resource_id=1,
        project_id=2,
        utilisation_percent=50,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 2, 1),
    )
    with pytest.raises(ValidationError):
        BulkCreateAllocationRequest(
            project_id=1,
            utilisation_percent=50,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 2, 1),
            items=[{"resource_id": 1}, {"resource_id": 1}],
        )
    bulk = BulkCreateAllocationRequest(
        project_id=1,
        utilisation_percent=40,
        from_date=date(2026, 1, 1),
        to_date=date(2026, 2, 1),
        items=[{"resource_id": 1, "role_key": "r1"}, {"resource_id": 2}],
    )
    assert len(bulk.items) == 2


def test_skill_requests():
    add = AddSkillRequest(
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    upd = UpdateSkillProficiencyRequest(proficiency_level=ProficiencyLevel.BEGINNER)
    assert add.category == SkillCategoryEnum.BACKEND
    assert upd.proficiency_level == ProficiencyLevel.BEGINNER


def test_milestone_and_timesheet_requests():
    AddMilestoneRequest(title="Ship", due_date=date(2026, 3, 1), story_points=5)
    UpdateMilestoneStatusRequest(status=MilestoneStatus.DONE)
    SubmitTimesheetRequest(
        week_start=date(2026, 1, 5),
        entries=[
            {
                "project_id": 1,
                "hours": Decimal("8"),
                "tags": [{"activity_tag_id": 1, "custom_label": None}],
            }
        ],
    )
    RestoreTimesheetComplianceRequest(week_start=date(2026, 1, 5))


def test_update_system_config_request():
    req = UpdateSystemConfigRequest(
        llm_provider=LlmProvider.GEMINI,
        scheduler_interval_hours=4,
        max_weekly_hours=40,
    )
    assert req.llm_provider == LlmProvider.GEMINI
