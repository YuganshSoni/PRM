from server.core.exceptions import (
    InvalidStoryPointsError,
    MilestoneNotFoundError,
    ProjectNotFoundError,
)
from server.models.enums import MilestoneStatus
from server.models.milestone import Milestone
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.schemas.requests.milestone import AddMilestoneRequest
from server.schemas.responses.milestone import StoryPointSummary


class MilestoneService:
    def __init__(
        self,
        milestone_repository: MilestoneRepository,
        project_repository: ProjectRepository,
    ) -> None:
        self._milestone_repository = milestone_repository
        self._project_repository = project_repository

    async def add_milestone(
        self, project_id: int, dto: AddMilestoneRequest
    ) -> Milestone:
        await self._require_project(project_id)
        if dto.story_points <= 0:
            raise InvalidStoryPointsError("Milestone story points must be greater than 0")

        sort_order = await self._milestone_repository.max_sort_order(project_id) + 1
        milestone = Milestone(
            project_id=project_id,
            title=dto.title,
            due_date=dto.due_date,
            story_points=dto.story_points,
            status=MilestoneStatus.NOT_STARTED,
            sort_order=sort_order,
        )
        return await self._milestone_repository.save(milestone)

    async def list_milestones(
        self, project_id: int
    ) -> tuple[list[Milestone], StoryPointSummary]:
        await self._require_project(project_id)
        milestones = await self._milestone_repository.find_by_project_id(project_id)
        summary = await self.compute_story_point_totals(project_id)
        return milestones, summary

    async def update_milestone_status(
        self, milestone_id: int, status: MilestoneStatus
    ) -> Milestone:
        milestone = await self._milestone_repository.get_by_id(milestone_id)
        if milestone is None:
            raise MilestoneNotFoundError("Milestone not found")

        milestone.status = status
        return await self._milestone_repository.save(milestone)

    async def compute_story_point_totals(self, project_id: int) -> StoryPointSummary:
        project = await self._require_project(project_id)
        completed = await self._milestone_repository.sum_done_story_points(project_id)
        total = project.total_story_points
        return StoryPointSummary(
            total=total,
            completed=completed,
            remaining=total - completed,
        )

    async def _require_project(self, project_id: int):
        project = await self._project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project
