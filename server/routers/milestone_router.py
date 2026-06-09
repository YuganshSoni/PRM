from typing import Annotated

from fastapi import APIRouter, Depends, status

from server.core.dependencies import dependency_provider
from server.models.enums import MilestoneStatus, UserRole
from server.models.milestone import Milestone
from server.models.user import User
from server.schemas.requests.milestone import (
    AddMilestoneRequest,
    UpdateMilestoneStatusRequest,
)
from server.schemas.response_values import MilestoneMessage
from server.schemas.responses.milestone import (
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneUpdatedResponse,
)
from server.services.milestone_service import MilestoneService


class MilestoneRouter:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["milestones"])
        self.router.add_api_route(
            "/projects/{project_id}/milestones",
            self.add_milestone,
            methods=["POST"],
            response_model=MilestoneResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "/projects/{project_id}/milestones",
            self.list_milestones,
            methods=["GET"],
            response_model=MilestoneListResponse,
        )
        self.router.add_api_route(
            "/milestones/{milestone_id}",
            self.update_milestone_status,
            methods=["PUT"],
            response_model=MilestoneUpdatedResponse,
        )

    async def add_milestone(
        self,
        project_id: int,
        body: AddMilestoneRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        milestone_service: MilestoneService = Depends(
            dependency_provider.get_milestone_service
        ),
    ) -> MilestoneResponse:
        milestone = await milestone_service.add_milestone(project_id, body)
        return self._to_milestone(milestone)

    async def list_milestones(
        self,
        project_id: int,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        milestone_service: MilestoneService = Depends(
            dependency_provider.get_milestone_service
        ),
    ) -> MilestoneListResponse:
        milestones, summary = await milestone_service.list_milestones(project_id)
        return MilestoneListResponse(
            items=[self._to_milestone(milestone) for milestone in milestones],
            story_point_summary=summary,
        )

    async def update_milestone_status(
        self,
        milestone_id: int,
        body: UpdateMilestoneStatusRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        milestone_service: MilestoneService = Depends(
            dependency_provider.get_milestone_service
        ),
    ) -> MilestoneUpdatedResponse:
        milestone = await milestone_service.update_milestone_status(
            milestone_id, body.status
        )
        return MilestoneUpdatedResponse(
            id=milestone.id,
            status=MilestoneStatus(milestone.status),
            message=MilestoneMessage.MILESTONE_UPDATED,
        )

    def _to_milestone(self, milestone: Milestone) -> MilestoneResponse:
        return MilestoneResponse(
            id=milestone.id,
            title=milestone.title,
            due_date=milestone.due_date,
            story_points=milestone.story_points,
            status=MilestoneStatus(milestone.status),
            sort_order=milestone.sort_order,
        )
