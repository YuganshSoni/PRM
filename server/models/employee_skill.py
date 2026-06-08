from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from server.models.employee import Employee


class EmployeeSkill(Base, CreatedAtMixin):
    __tablename__ = "employee_skills"
    __table_args__ = (UniqueConstraint("employee_id", "skill_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    skill_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20), index=True)
    proficiency_level: Mapped[str] = mapped_column(String(20))

    employee: Mapped["Employee"] = relationship(back_populates="skills")
