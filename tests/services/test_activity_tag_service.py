from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.schemas.responses.activity_tag import ActivityTagListResponse
from server.services.activity_tag_service import ActivityTagService


@pytest.mark.asyncio
async def test_list_predefined_tags_maps_repository_rows():
    repo = AsyncMock()
    repo.list_predefined_ordered.return_value = [
        SimpleNamespace(id=1, name="Development", display_order=1),
        SimpleNamespace(id=2, name="Meeting", display_order=2),
    ]
    service = ActivityTagService(repo)

    result = await service.list_predefined_tags()

    assert isinstance(result, ActivityTagListResponse)
    assert len(result.items) == 2
    assert result.items[0].name == "Development"
    assert result.items[1].display_order == 2
    repo.list_predefined_ordered.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_predefined_tags_empty():
    repo = AsyncMock()
    repo.list_predefined_ordered.return_value = []
    service = ActivityTagService(repo)

    result = await service.list_predefined_tags()

    assert result.items == []
