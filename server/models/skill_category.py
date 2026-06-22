from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.models.skill import Skill



class SkillCategory(Base):
    __tablename__ = "skill_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    skills: Mapped[list["Skill"]] = relationship(back_populates="category")
