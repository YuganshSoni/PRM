from typing import Annotated

from fastapi import APIRouter, Depends, status

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.ai import SkillMatchRequest, TeamBuildRequest
from server.schemas.responses.ai import (
    RiskSummaryResponse,
    SkillMatchResponse,
    TeamBuildResponse,
)
from server.services.ai_service import AIService


class AIRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.router.add_api_route(
            "/skill-match",
            self.skill_match,
            methods=["POST"],
            response_model=SkillMatchResponse,
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/risk-summary/{project_id}",
            self.risk_summary,
            methods=["POST"],
            response_model=RiskSummaryResponse,
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/team-build",
            self.team_build,
            methods=["POST"],
            response_model=TeamBuildResponse,
            status_code=status.HTTP_200_OK,
        )

    async def skill_match(
        self,
        body: SkillMatchRequest,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        ai_service: AIService = Depends(dependency_provider.get_ai_service),
    ) -> SkillMatchResponse:
        return await ai_service.skill_match(_manager, body)

    async def risk_summary(
        self,
        project_id: int,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        ai_service: AIService = Depends(dependency_provider.get_ai_service),
    ) -> RiskSummaryResponse:
        return await ai_service.risk_summary(_manager, project_id)

    async def team_build(
        self,
        body: TeamBuildRequest,
        _manager: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.MANAGER))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        ai_service: AIService = Depends(dependency_provider.get_ai_service),
    ) -> TeamBuildResponse:
        return await ai_service.team_build(_manager, body)
