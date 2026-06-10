from server.repositories.activity_tag_repository import ActivityTagRepository
from server.schemas.responses.activity_tag import ActivityTagListResponse, ActivityTagResponse


class ActivityTagService:
    def __init__(self, activity_tag_repository: ActivityTagRepository) -> None:
        self._activity_tag_repository = activity_tag_repository

    async def list_predefined_tags(self) -> ActivityTagListResponse:
        tags = await self._activity_tag_repository.list_predefined_ordered()
        return ActivityTagListResponse(
            items=[
                ActivityTagResponse(
                    id=tag.id,
                    name=tag.name,
                    display_order=tag.display_order,
                )
                for tag in tags
            ]
        )
