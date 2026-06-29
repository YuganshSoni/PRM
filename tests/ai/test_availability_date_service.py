from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.ai.services.availability_date_service import AvailabilityDateService


@pytest.mark.asyncio
async def test_compute_available_from_today_when_no_allocations(monkeypatch):
    repo = AsyncMock()
    repo.find_active_by_resource.return_value = []
    service = AvailabilityDateService(repo)
    fixed_today = date(2026, 7, 14)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return fixed_today

    monkeypatch.setattr(
        "server.ai.services.availability_date_service.date",
        FixedDate,
    )

    result = await service.compute_available_from(7)

    assert result == fixed_today
    repo.find_active_by_resource.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_compute_available_from_day_after_latest_end():
    repo = AsyncMock()
    early = MagicMock(to_date=date(2026, 1, 10))
    late = MagicMock(to_date=date(2026, 3, 20))
    repo.find_active_by_resource.return_value = [early, late]
    service = AvailabilityDateService(repo)

    result = await service.compute_available_from(3)

    assert result == date(2026, 3, 20) + timedelta(days=1)
    assert result == date(2026, 3, 21)
