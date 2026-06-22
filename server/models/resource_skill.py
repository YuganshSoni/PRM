from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.resource import Resource
    from server.models.skill import Skill


class ResourceSkill(Base, TimestampMixin):
    __tablename__ = "resource_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), index=True
    )
    proficiency_level: Mapped[str] = mapped_column(String(20))

    resource: Mapped["Resource"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="resource_skills")
