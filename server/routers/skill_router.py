from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.skill import UpdateSkillProficiencyRequest
from server.schemas.response_values import SkillMessage
from server.schemas.responses.skill import SkillActionResponse, SkillResponse
from server.services.skill_service import SkillService


class SkillRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/skills", tags=["skills"])
        self.router.add_api_route(
            "/{skill_id}",
            self.update_proficiency,
            methods=["PUT"],
            response_model=SkillActionResponse,
        )
        self.router.add_api_route(
            "/{skill_id}",
            self.remove_skill,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
        )

    async def update_proficiency(
        self,
        skill_id: int,
        body: UpdateSkillProficiencyRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> SkillActionResponse:
        skill = await skill_service.update_proficiency(skill_id, body)
        return SkillActionResponse(id=skill.id, message=SkillMessage.SKILL_UPDATED)

    async def remove_skill(
        self,
        skill_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        skill_service: SkillService = Depends(dependency_provider.get_skill_service),
    ) -> Response:
        await skill_service.remove_skill(skill_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
