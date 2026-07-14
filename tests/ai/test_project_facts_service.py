from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.ai.services.project_facts_service import ProjectFactsService
from server.core.exceptions import ProjectNotFoundError
from server.models.enums import HealthStatus, MilestoneStatus, ProjectStatus


def _service(
    *,
    project_repo=None,
    milestone_repo=None,
    allocation_repo=None,
    health_service=None,
) -> ProjectFactsService:
    return ProjectFactsService(
        project_repository=project_repo or AsyncMock(),
        milestone_repository=milestone_repo or AsyncMock(),
        allocation_repository=allocation_repo or AsyncMock(),
        project_health_service=health_service or AsyncMock(),
    )


@pytest.mark.asyncio
async def test_collect_raises_when_project_missing():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = None
    with pytest.raises(ProjectNotFoundError):
        await _service(project_repo=project_repo).collect(1, 100)


@pytest.mark.asyncio
async def test_collect_raises_when_manager_mismatch():
    project = SimpleNamespace(id=1, manager_id=999)
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    with pytest.raises(ProjectNotFoundError):
        await _service(project_repo=project_repo).collect(1, 100)


@pytest.mark.asyncio
async def test_collect_builds_facts_dto():
    today = date.today()
    project = SimpleNamespace(
        id=5,
        name="Apollo",
        manager_id=100,
        status=ProjectStatus.ACTIVE,
        end_date=today + timedelta(days=30),
    )
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project

    health_service = AsyncMock()
    snapshot = SimpleNamespace(health_status=HealthStatus.AT_RISK)
    health_service.get_snapshot.return_value = snapshot
    health_service.get_risk_flags_for_project.return_value = [
        SimpleNamespace(flag_text="Logged only 2h", is_positive=False),
        SimpleNamespace(flag_text="Looking good", is_positive=True),
        SimpleNamespace(flag_text="Scope creep", is_positive=False),
    ]

    overdue = SimpleNamespace(
        title="Late",
        due_date=today - timedelta(days=2),
        status=MilestoneStatus.NOT_STARTED,
    )
    done = SimpleNamespace(
        title="Done",
        due_date=today - timedelta(days=1),
        status=MilestoneStatus.DONE,
    )
    milestone_repo = AsyncMock()
    milestone_repo.find_by_project_id.return_value = [overdue, done]

    with_user = MagicMock()
    with_user.utilisation_percent = 50
    with_user.resource.user.full_name = "Ada"

    without_user = MagicMock()
    without_user.utilisation_percent = 25
    without_user.resource = SimpleNamespace(user=None)

    allocation_repo = AsyncMock()
    allocation_repo.find_active_by_project.return_value = [with_user, without_user]

    facts = await _service(
        project_repo=project_repo,
        milestone_repo=milestone_repo,
        allocation_repo=allocation_repo,
        health_service=health_service,
    ).collect(5, 100)

    assert facts.project_id == 5
    assert facts.project_name == "Apollo"
    assert facts.health_status == HealthStatus.AT_RISK.value
    assert facts.milestones[0].is_overdue is True
    assert facts.milestones[1].is_overdue is False
    assert facts.allocations[0].resource_name == "Ada"
    assert facts.allocations[1].resource_name == "Resource"
    assert "Scope creep" in facts.risk_flags
    assert "Looking good" not in facts.risk_flags
    assert any("logged only" in note.lower() for note in facts.hours_notes)
    assert "Apollo" in facts.to_prompt_text()


@pytest.mark.asyncio
async def test_collect_handles_null_health_snapshot():
    project = SimpleNamespace(
        id=5,
        name="Apollo",
        manager_id=100,
        status=ProjectStatus.ACTIVE,
        end_date=date.today(),
    )
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = project
    health_service = AsyncMock()
    health_service.get_snapshot.return_value = None
    health_service.get_risk_flags_for_project.return_value = []
    milestone_repo = AsyncMock()
    milestone_repo.find_by_project_id.return_value = []
    allocation_repo = AsyncMock()
    allocation_repo.find_active_by_project.return_value = []

    facts = await _service(
        project_repo=project_repo,
        milestone_repo=milestone_repo,
        allocation_repo=allocation_repo,
        health_service=health_service,
    ).collect(5, 100)

    assert facts.health_status is None
    assert facts.milestones == []
    assert facts.allocations == []
