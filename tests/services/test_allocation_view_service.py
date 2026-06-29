from unittest.mock import AsyncMock

import pytest

from server.services.allocation_view_service import AllocationViewService


@pytest.mark.asyncio
async def test_list_allocations_returns_items_and_total():
    repo = AsyncMock()
    repo.list_active.return_value = ["a1", "a2"]
    repo.count_active.return_value = 2
    service = AllocationViewService(repo)

    result = await service.list_allocations(
        resource_id=1,
        project_id=2,
        resource_name="Ada",
        project_name="Engine",
        limit=10,
        offset=0,
    )

    assert result.items == ["a1", "a2"]
    assert result.total == 2
    repo.list_active.assert_awaited_once_with(
        resource_id=1,
        project_id=2,
        resource_name="Ada",
        project_name="Engine",
        limit=10,
        offset=0,
    )
    repo.count_active.assert_awaited_once_with(
        resource_id=1,
        project_id=2,
        resource_name="Ada",
        project_name="Engine",
    )


@pytest.mark.asyncio
async def test_list_allocations_with_no_filters():
    repo = AsyncMock()
    repo.list_active.return_value = []
    repo.count_active.return_value = 0
    service = AllocationViewService(repo)

    result = await service.list_allocations(
        resource_id=None,
        project_id=None,
        resource_name=None,
        project_name=None,
        limit=20,
        offset=5,
    )

    assert result.items == []
    assert result.total == 0
