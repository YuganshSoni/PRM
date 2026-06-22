from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.models.user import User



class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")
