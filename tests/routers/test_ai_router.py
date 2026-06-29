from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from server.core.dependencies import dependency_provider
from server.core.exception_handlers import ExceptionHandlerRegistrar
from server.models.enums import ProficiencyLevel, SkillCategoryEnum, UserRole
from server.routers.ai_router import AIRouter
from server.schemas.responses.ai import (
    ParsedTeamRoleResponse,
    RiskSummaryResponse,
    SkillMatchCandidateResponse,
    SkillMatchResponse,
    TeamBuildResponse,
    TeamRoleMatchResponse,
)


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    ExceptionHandlerRegistrar().register(application)
    application.include_router(AIRouter().router)
    return application


def _manager():
    user = MagicMock()
    user.id = 10
    user.force_password_change = False
    user.role = SimpleNamespace(name=UserRole.MANAGER.value)
    return user


def _override_ai(app: FastAPI, ai_service):
    manager = _manager()

    async def override_user():
        return manager

    async def override_ai_service():
        return ai_service

    app.dependency_overrides[dependency_provider.get_current_user] = override_user
    app.dependency_overrides[dependency_provider.get_ai_service] = override_ai_service
    return manager


def test_skill_match_route(app: FastAPI):
    ai_service = AsyncMock()
    ai_service.skill_match.return_value = SkillMatchResponse(
        items=[
            SkillMatchCandidateResponse(
                resource_id=1,
                resource_name="Ada",
                reason="Strong Python",
                free_hours_per_week=20.0,
                suggested_utilisation_percent=50,
                rank=1,
            )
        ],
        message=None,
        llm_invoked=True,
        weekly_hours_requested=20,
        requirement_parse_invoked=True,
        parsed_summary="Need Python help",
    )
    manager = _override_ai(app, ai_service)
    client = TestClient(app)

    response = client.post(
        "/ai/skill-match",
        json={"requirement": "Need a Python engineer for 20 hours"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["llm_invoked"] is True
    assert body["items"][0]["resource_name"] == "Ada"
    ai_service.skill_match.assert_awaited_once()
    args = ai_service.skill_match.await_args.args
    assert args[0] is manager
    assert args[1].requirement.startswith("Need a Python")


def test_risk_summary_route(app: FastAPI):
    ai_service = AsyncMock()
    ai_service.risk_summary.return_value = RiskSummaryResponse(
        project_id=7,
        project_name="Apollo",
        summary="Milestones are overdue.",
        llm_invoked=True,
    )
    manager = _override_ai(app, ai_service)
    client = TestClient(app)

    response = client.post("/ai/risk-summary/7")

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == 7
    assert "overdue" in body["summary"].lower()
    ai_service.risk_summary.assert_awaited_once_with(manager, 7)


def test_team_build_route(app: FastAPI):
    ai_service = AsyncMock()
    ai_service.team_build.return_value = TeamBuildResponse(
        project_id=3,
        parsed_roles=[
            ParsedTeamRoleResponse(
                role_key="role_1",
                role_title="Backend",
                skill_names=["Python"],
                skill_category=SkillCategoryEnum.BACKEND,
                min_proficiency=ProficiencyLevel.INTERMEDIATE,
            )
        ],
        matches=[
            TeamRoleMatchResponse(
                role_key="role_1",
                role_title="Backend",
                resource_id=1,
                resource_name="Ada",
                reason="Bench match",
                match_score=88,
            )
        ],
        gaps=[],
        llm_invoked=True,
    )
    manager = _override_ai(app, ai_service)
    client = TestClient(app)

    response = client.post(
        "/ai/team-build",
        json={
            "requirement": "Need one backend engineer on the bench",
            "project_id": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == 3
    assert body["matches"][0]["resource_name"] == "Ada"
    ai_service.team_build.assert_awaited_once()
    assert ai_service.team_build.await_args.args[0] is manager
