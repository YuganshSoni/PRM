from server.models.enums import (
    ProficiencyLevel,
    SkillCategoryEnum,
    UserRole,
    UserStatus,
)
from server.schemas.response_values import SkillMessage, UserMessage
from server.schemas.responses.skill import (
    SkillActionResponse,
    SkillListResponse,
    SkillResponse,
)
from server.schemas.responses.user import (
    UserActionResponse,
    UserCreatedResponse,
    UserListResponse,
    UserResponse,
    UserSummaryResponse,
)


def test_skill_response_schemas():
    skill = SkillResponse(
        id=1,
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    listed = SkillListResponse(items=[skill])
    action = SkillActionResponse(id=1, message=SkillMessage.SKILL_UPDATED)

    assert listed.items[0].skill_name == "Python"
    assert skill.category == SkillCategoryEnum.BACKEND
    assert action.message == SkillMessage.SKILL_UPDATED


def test_user_response_schemas():
    summary = UserSummaryResponse(
        id=1,
        username="ada",
        full_name="Ada Lovelace",
        role=UserRole.RESOURCE,
        status=UserStatus.ACTIVE,
    )
    detail = UserResponse(
        id=1,
        username="ada",
        email="ada@example.com",
        full_name="Ada Lovelace",
        role=UserRole.RESOURCE,
        status=UserStatus.ACTIVE,
        force_password_change=True,
    )
    created = UserCreatedResponse(
        id=1,
        username="ada",
        role=UserRole.RESOURCE,
        message=UserMessage.ACCOUNT_CREATED,
    )
    listed = UserListResponse(
        items=[summary],
        total=1,
        active_count=1,
        inactive_count=0,
        limit=50,
        offset=0,
    )
    action = UserActionResponse(
        user_id=1, message=UserMessage.PASSWORD_RESET
    )

    assert detail.force_password_change is True
    assert created.message == UserMessage.ACCOUNT_CREATED
    assert listed.total == 1
    assert action.message == UserMessage.PASSWORD_RESET
