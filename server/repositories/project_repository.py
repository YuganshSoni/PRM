from sqlalchemy.ext.asyncio import AsyncSession

from server.models.project import Project
from server.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)
