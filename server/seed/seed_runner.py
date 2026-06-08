import asyncio
import sys

from server.core.database import get_database_manager
from server.core.security import PasswordHasher
from server.seed.activity_tag_seeder import ActivityTagSeeder
from server.seed.bootstrap_admin_seeder import BootstrapAdminSeeder
from server.seed.system_config_seeder import SystemConfigSeeder


class SeedRunner:
    def __init__(self) -> None:
        self._seeders = [
            BootstrapAdminSeeder(PasswordHasher()),
            SystemConfigSeeder(),
            ActivityTagSeeder(),
        ]

    async def run(self) -> None:
        manager = get_database_manager()
        async with manager.session_factory() as session:
            async with session.begin():
                for seeder in self._seeders:
                    await seeder.run(session)
        await manager.dispose()

    def run_cli(self) -> None:
        try:
            asyncio.run(self.run())
            print("Seed completed.")
        except Exception as exc:
            print(f"Seed failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    SeedRunner().run_cli()
