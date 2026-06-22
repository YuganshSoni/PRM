from typing import Annotated

from fastapi import APIRouter, Depends

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.responses.activity_tag import ActivityTagListResponse
from server.services.activity_tag_service import ActivityTagService


class ActivityTagRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/activity-tags", tags=["activity-tags"])
        self.router.add_api_route(
            "",
            self.list_activity_tags,
            methods=["GET"],
            response_model=ActivityTagListResponse,
        )

    async def list_activity_tags(
        self,
        _resource: Annotated[
            User, Depends(dependency_provider.require_role(UserRole.RESOURCE))
        ],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        activity_tag_service: ActivityTagService = Depends(
            dependency_provider.get_activity_tag_service
        ),
    ) -> ActivityTagListResponse:
        return await activity_tag_service.list_predefined_tags()
