from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

if TYPE_CHECKING:
    from server.models.timesheet_entry_tag import TimesheetEntryTag


class ActivityTag(Base):
    __tablename__ = "activity_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_predefined: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer)

    entry_tags: Mapped[list["TimesheetEntryTag"]] = relationship(
        back_populates="activity_tag"
    )
