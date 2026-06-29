from unittest.mock import MagicMock

from server.models.enums import ResourceStatusEnum, SkillCategoryEnum
from server.services.resource_mapper import ResourceMapper


def _resource():
    resource = MagicMock()
    resource.user.full_name = "Ada Lovelace"
    resource.user.email = "ada@example.com"
    resource.department.name = "Engineering"
    resource.designation.name = "Senior Engineer"
    resource.resource_status.name = "BENCH"
    return resource


def test_full_name():
    assert ResourceMapper.full_name(_resource()) == "Ada Lovelace"


def test_email():
    assert ResourceMapper.email(_resource()) == "ada@example.com"


def test_department_name():
    assert ResourceMapper.department_name(_resource()) == "Engineering"


def test_designation_name():
    assert ResourceMapper.designation_name(_resource()) == "Senior Engineer"


def test_status():
    assert ResourceMapper.status(_resource()) == ResourceStatusEnum.BENCH


def test_status_allocated():
    resource = _resource()
    resource.resource_status.name = "ALLOCATED"
    assert ResourceMapper.status(resource) == ResourceStatusEnum.ALLOCATED


def test_skill_name_and_category():
    resource_skill = MagicMock()
    resource_skill.skill.name = "Python"
    resource_skill.skill.category.name = "BACKEND"

    assert ResourceMapper.skill_name(resource_skill) == "Python"
    assert ResourceMapper.skill_category(resource_skill) == SkillCategoryEnum.BACKEND
