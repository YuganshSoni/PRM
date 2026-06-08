from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

if TYPE_CHECKING:
    from server.models.activity_tag import ActivityTag
    from server.models.timesheet_entry import TimesheetEntry


class TimesheetEntryTag(Base):
    __tablename__ = "timesheet_entry_tags"
    __table_args__ = (UniqueConstraint("timesheet_entry_id", "activity_tag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timesheet_entry_id: Mapped[int] = mapped_column(
        ForeignKey("timesheet_entries.id", ondelete="CASCADE"), index=True
    )
    activity_tag_id: Mapped[int] = mapped_column(
        ForeignKey("activity_tags.id", ondelete="RESTRICT")
    )
    custom_label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    entry: Mapped["TimesheetEntry"] = relationship(back_populates="tags")
    activity_tag: Mapped["ActivityTag"] = relationship(back_populates="entry_tags")
