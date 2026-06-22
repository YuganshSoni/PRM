from dataclasses import dataclass

from server.models.allocation import Allocation
from server.repositories.allocation_repository import AllocationRepository


@dataclass(frozen=True)
class AllocationListResult:
    items: list[Allocation]
    total: int


class AllocationViewService:
    def __init__(self, allocation_repository: AllocationRepository) -> None:
        self._allocation_repository = allocation_repository

    async def list_allocations(
        self,
        *,
        resource_id: int | None,
        project_id: int | None,
        resource_name: str | None,
        project_name: str | None,
        limit: int,
        offset: int,
    ) -> AllocationListResult:
        items = await self._allocation_repository.list_active(
            resource_id=resource_id,
            project_id=project_id,
            resource_name=resource_name,
            project_name=project_name,
            limit=limit,
            offset=offset,
        )
        total = await self._allocation_repository.count_active(
            resource_id=resource_id,
            project_id=project_id,
            resource_name=resource_name,
            project_name=project_name,
        )
        return AllocationListResult(items=items, total=total)
