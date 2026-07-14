from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.models.resource_skill import ResourceSkill
    from server.models.skill_category import SkillCategory



class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("skill_categories.id", ondelete="RESTRICT"), index=True
    )

    category: Mapped["SkillCategory"] = relationship(back_populates="skills")
    resource_skills: Mapped[list["ResourceSkill"]] = relationship(back_populates="skill")
