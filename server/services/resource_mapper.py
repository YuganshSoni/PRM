from server.models.enums import ResourceStatusEnum, SkillCategoryEnum
from server.models.resource import Resource
from server.models.resource_skill import ResourceSkill


class ResourceMapper:
    """Maps normalized ORM graphs to API-facing display values."""

    @staticmethod
    def full_name(resource: Resource) -> str:
        return resource.user.full_name

    @staticmethod
    def email(resource: Resource) -> str:
        return resource.user.email

    @staticmethod
    def department_name(resource: Resource) -> str:
        return resource.department.name

    @staticmethod
    def designation_name(resource: Resource) -> str:
        return resource.designation.name

    @staticmethod
    def status(resource: Resource) -> ResourceStatusEnum:
        return ResourceStatusEnum(resource.resource_status.name)

    @staticmethod
    def skill_name(resource_skill: ResourceSkill) -> str:
        return resource_skill.skill.name

    @staticmethod
    def skill_category(resource_skill: ResourceSkill) -> SkillCategoryEnum:
        return SkillCategoryEnum(resource_skill.skill.category.name)
