from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.core.exceptions import (
    DuplicateSkillError,
    EmployeeNotFoundError,
    SkillNotFoundError,
)
from server.models.enums import ProficiencyLevel, SkillCategoryEnum
from server.schemas.requests.skill import AddSkillRequest, UpdateSkillProficiencyRequest
from server.services.skill_service import SkillService


@pytest.fixture
def skill_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def resource_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def master_skill_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(skill_repo, resource_repo, master_skill_repo) -> SkillService:
    return SkillService(skill_repo, resource_repo, master_skill_repo)


@pytest.mark.asyncio
async def test_add_skill_requires_resource(service, resource_repo):
    resource_repo.get_by_id.return_value = None
    dto = AddSkillRequest(
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    with pytest.raises(EmployeeNotFoundError):
        await service.add_skill(10, dto)


@pytest.mark.asyncio
async def test_add_skill_rejects_duplicate(service, resource_repo, skill_repo):
    resource_repo.get_by_id.return_value = SimpleNamespace(id=10)
    skill_repo.find_by_resource_and_name.return_value = SimpleNamespace(id=1)
    dto = AddSkillRequest(
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    with pytest.raises(DuplicateSkillError):
        await service.add_skill(10, dto)


@pytest.mark.asyncio
async def test_add_skill_happy_path(
    service, resource_repo, skill_repo, master_skill_repo
):
    resource_repo.get_by_id.return_value = SimpleNamespace(id=10)
    skill_repo.find_by_resource_and_name.return_value = None
    master_skill_repo.find_or_create.return_value = SimpleNamespace(id=55)
    saved = SimpleNamespace(id=99)
    loaded = SimpleNamespace(id=99, skill_id=55)
    skill_repo.save.return_value = saved
    skill_repo.get_by_id_with_relations.return_value = loaded

    dto = AddSkillRequest(
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    result = await service.add_skill(10, dto)

    assert result is loaded
    skill_repo.save.assert_awaited_once()
    master_skill_repo.find_or_create.assert_awaited_once_with(
        "Python", SkillCategoryEnum.BACKEND.value
    )


@pytest.mark.asyncio
async def test_add_skill_raises_if_reload_fails(
    service, resource_repo, skill_repo, master_skill_repo
):
    resource_repo.get_by_id.return_value = SimpleNamespace(id=10)
    skill_repo.find_by_resource_and_name.return_value = None
    master_skill_repo.find_or_create.return_value = SimpleNamespace(id=55)
    skill_repo.save.return_value = SimpleNamespace(id=99)
    skill_repo.get_by_id_with_relations.return_value = None

    dto = AddSkillRequest(
        skill_name="Python",
        category=SkillCategoryEnum.BACKEND,
        proficiency_level=ProficiencyLevel.BEGINNER,
    )
    with pytest.raises(SkillNotFoundError):
        await service.add_skill(10, dto)


@pytest.mark.asyncio
async def test_list_skills(service, resource_repo, skill_repo):
    resource_repo.get_by_id.return_value = SimpleNamespace(id=10)
    skill_repo.find_by_resource_id.return_value = [MagicMock(), MagicMock()]
    result = await service.list_skills(10)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_update_proficiency_not_found(service, skill_repo):
    skill_repo.get_by_id.return_value = None
    dto = UpdateSkillProficiencyRequest(proficiency_level=ProficiencyLevel.INTERMEDIATE)
    with pytest.raises(SkillNotFoundError):
        await service.update_proficiency(1, dto)


@pytest.mark.asyncio
async def test_update_proficiency_happy_path(service, skill_repo):
    skill = SimpleNamespace(id=1, proficiency_level="BEGINNER")
    skill_repo.get_by_id.return_value = skill
    skill_repo.save.return_value = skill
    loaded = SimpleNamespace(id=1, proficiency_level="ADVANCED")
    skill_repo.get_by_id_with_relations.return_value = loaded

    dto = UpdateSkillProficiencyRequest(proficiency_level=ProficiencyLevel.ADVANCED)
    result = await service.update_proficiency(1, dto)

    assert result is loaded
    assert skill.proficiency_level == ProficiencyLevel.ADVANCED.value


@pytest.mark.asyncio
async def test_remove_skill_not_found(service, skill_repo):
    skill_repo.get_by_id.return_value = None
    with pytest.raises(SkillNotFoundError):
        await service.remove_skill(1)


@pytest.mark.asyncio
async def test_remove_skill_deletes(service, skill_repo):
    skill = SimpleNamespace(id=1)
    skill_repo.get_by_id.return_value = skill
    await service.remove_skill(1)
    skill_repo.delete.assert_awaited_once_with(skill)
