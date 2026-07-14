from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.core.exceptions import (
    InvalidStoryPointsError,
    MilestoneNotFoundError,
    ProjectNotFoundError,
)
from server.models.enums import MilestoneStatus
from server.schemas.requests.milestone import AddMilestoneRequest
from server.services.milestone_service import MilestoneService


@pytest.fixture
def milestone_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(milestone_repo, project_repo) -> MilestoneService:
    return MilestoneService(milestone_repo, project_repo)


@pytest.mark.asyncio
async def test_add_milestone_requires_project(service, project_repo):
    project_repo.get_by_id.return_value = None
    dto = AddMilestoneRequest(
        title="M1", due_date=date(2026, 8, 1), story_points=5
    )
    with pytest.raises(ProjectNotFoundError):
        await service.add_milestone(1, dto)


@pytest.mark.asyncio
async def test_add_milestone_rejects_non_positive_story_points(service, project_repo):
    project_repo.get_by_id.return_value = SimpleNamespace(id=1, total_story_points=10)
    # pydantic Field(gt=0) blocks 0 on DTO; exercise service check via MagicMock
    from unittest.mock import MagicMock

    dto = MagicMock()
    dto.story_points = 0
    dto.title = "M1"
    dto.due_date = date(2026, 8, 1)
    with pytest.raises(InvalidStoryPointsError):
        await service.add_milestone(1, dto)


@pytest.mark.asyncio
async def test_add_milestone_happy_path(service, project_repo, milestone_repo):
    project_repo.get_by_id.return_value = SimpleNamespace(id=1, total_story_points=10)
    milestone_repo.max_sort_order.return_value = 2
    saved = SimpleNamespace(id=9, sort_order=3)
    milestone_repo.save.return_value = saved

    dto = AddMilestoneRequest(
        title="M1", due_date=date(2026, 8, 1), story_points=5
    )
    result = await service.add_milestone(1, dto)

    assert result is saved
    created = milestone_repo.save.await_args.args[0]
    assert created.sort_order == 3
    assert created.status == MilestoneStatus.NOT_STARTED


@pytest.mark.asyncio
async def test_list_milestones(service, project_repo, milestone_repo):
    project_repo.get_by_id.return_value = SimpleNamespace(id=1, total_story_points=20)
    milestone_repo.find_by_project_id.return_value = [SimpleNamespace(id=1)]
    milestone_repo.sum_done_story_points.return_value = 8

    milestones, summary = await service.list_milestones(1)

    assert len(milestones) == 1
    assert summary.total == 20
    assert summary.completed == 8
    assert summary.remaining == 12


@pytest.mark.asyncio
async def test_update_milestone_status_not_found(service, milestone_repo):
    milestone_repo.get_by_id.return_value = None
    with pytest.raises(MilestoneNotFoundError):
        await service.update_milestone_status(1, MilestoneStatus.DONE)


@pytest.mark.asyncio
async def test_update_milestone_status_happy_path(service, milestone_repo):
    milestone = SimpleNamespace(id=1, status=MilestoneStatus.NOT_STARTED)
    milestone_repo.get_by_id.return_value = milestone
    milestone_repo.save.return_value = milestone

    result = await service.update_milestone_status(1, MilestoneStatus.DONE)

    assert result.status == MilestoneStatus.DONE


@pytest.mark.asyncio
async def test_compute_story_point_totals_requires_project(service, project_repo):
    project_repo.get_by_id.return_value = None
    with pytest.raises(ProjectNotFoundError):
        await service.compute_story_point_totals(1)
