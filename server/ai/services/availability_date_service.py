from datetime import date, timedelta

from server.repositories.allocation_repository import AllocationRepository


class AvailabilityDateService:
    def __init__(self, allocation_repository: AllocationRepository) -> None:
        self._allocation_repository = allocation_repository

    async def compute_available_from(self, resource_id: int) -> date | None:
        allocations = await self._allocation_repository.find_active_by_resource(
            resource_id
        )
        if not allocations:
            return date.today()
        latest_end = max(allocation.to_date for allocation in allocations)
        return latest_end + timedelta(days=1)
