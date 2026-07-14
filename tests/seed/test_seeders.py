from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.seed.activity_tag_seeder import PREDEFINED_TAGS, ActivityTagSeeder
from server.seed.bootstrap_admin_seeder import BootstrapAdminSeeder
from server.seed.lookup_data_seeder import (
    PREDEFINED_RESOURCE_STATUSES,
    PREDEFINED_ROLES,
    PREDEFINED_SKILL_CATEGORIES,
    LookupDataSeeder,
)
from server.seed.seed_runner import SeedRunner
from server.seed.system_config_seeder import SystemConfigSeeder


def _session() -> MagicMock:
    session = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


def _scalars_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = items[0] if items else None
    return result


@pytest.mark.asyncio
async def test_activity_tag_seeder_skips_existing_and_adds_missing():
    session = _session()
    existing = [SimpleNamespace(name="Backend API Development")]
    session.execute.return_value = _scalars_result(existing)

    await ActivityTagSeeder().run(session)

    assert session.add.call_count == len(PREDEFINED_TAGS) - 1
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_activity_tag_seeder_noop_when_all_present():
    session = _session()
    existing = [SimpleNamespace(name=name) for _, name in PREDEFINED_TAGS]
    session.execute.return_value = _scalars_result(existing)

    await ActivityTagSeeder().run(session)

    session.add.assert_not_called()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_lookup_data_seeder_adds_missing_lookups():
    session = _session()
    session.execute.side_effect = [
        _scalars_result([]),
        _scalars_result([]),
        _scalars_result([]),
    ]

    await LookupDataSeeder().run(session)

    expected = (
        len(PREDEFINED_ROLES)
        + len(PREDEFINED_RESOURCE_STATUSES)
        + len(PREDEFINED_SKILL_CATEGORIES)
    )
    assert session.add.call_count == expected
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_system_config_seeder_skips_when_row_exists():
    session = _session()
    session.execute.return_value = _scalars_result([SimpleNamespace(id=1)])

    await SystemConfigSeeder().run(session)

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_system_config_seeder_adds_default_row():
    session = _session()
    session.execute.return_value = _scalars_result([])

    await SystemConfigSeeder().run(session)

    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_admin_seeder_skips_existing_admin():
    hasher = MagicMock()
    session = _session()
    session.execute.return_value = _scalars_result([SimpleNamespace(username="admin")])

    await BootstrapAdminSeeder(hasher).run(session)

    hasher.hash.assert_not_called()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_admin_seeder_creates_admin():
    hasher = MagicMock()
    hasher.hash.return_value = "hashed"
    session = _session()
    admin_role = SimpleNamespace(id=99, name="ADMIN")
    first = MagicMock()
    first.scalar_one_or_none.return_value = None
    second = MagicMock()
    second.scalar_one_or_none.return_value = admin_role
    session.execute.side_effect = [first, second]

    await BootstrapAdminSeeder(hasher).run(session)

    hasher.hash.assert_called_once_with(BootstrapAdminSeeder.ADMIN_DEFAULT_PASSWORD)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_admin_seeder_requires_admin_role():
    hasher = MagicMock()
    session = _session()
    first = MagicMock()
    first.scalar_one_or_none.return_value = None
    second = MagicMock()
    second.scalar_one_or_none.return_value = None
    session.execute.side_effect = [first, second]

    with pytest.raises(RuntimeError, match="ADMIN role not found"):
        await BootstrapAdminSeeder(hasher).run(session)


@pytest.mark.asyncio
async def test_seed_runner_runs_all_seeders():
    runner = SeedRunner()
    seeder_a = AsyncMock()
    seeder_b = AsyncMock()
    runner._seeders = [seeder_a, seeder_b]

    session = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    session.begin = MagicMock(return_value=begin_cm)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    manager = MagicMock()
    manager.session_factory.return_value = session_cm
    manager.dispose = AsyncMock()

    with patch(
        "server.seed.seed_runner.get_database_manager",
        return_value=manager,
    ):
        await runner.run()

    seeder_a.run.assert_awaited_once_with(session)
    seeder_b.run.assert_awaited_once_with(session)
    manager.dispose.assert_awaited_once()
