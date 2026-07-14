import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from server.core.database import get_database_manager
from server.models.activity_tag import ActivityTag
from server.models.enums import LlmProvider
from server.models.system_config import SystemConfig
from server.models.user import User
from server.repositories.user_repository import UserRepository
from server.seed.bootstrap_admin_seeder import BootstrapAdminSeeder


class DatabaseVerifier:
    async def verify(self) -> None:
        manager = get_database_manager()
        async with manager.session_factory() as session:
            admin_count = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.username == BootstrapAdminSeeder.ADMIN_USERNAME)
            )
            if admin_count != 1:
                raise RuntimeError(f"Expected 1 admin user, found {admin_count}")

            tag_count = await session.scalar(
                select(func.count()).select_from(ActivityTag)
            )
            if tag_count != 11:
                raise RuntimeError(f"Expected 11 activity tags, found {tag_count}")

            config = await session.get(SystemConfig, 1)
            if config is None:
                raise RuntimeError("system_config row missing")
            if config.llm_provider != LlmProvider.GEMINI:
                raise RuntimeError("system_config llm_provider mismatch")
            if config.scheduler_interval_hours != 4:
                raise RuntimeError("system_config scheduler_interval_hours mismatch")
            if config.max_weekly_hours != 40:
                raise RuntimeError("system_config max_weekly_hours mismatch")

            repo = UserRepository(session)
            admin = await repo.find_by_username(BootstrapAdminSeeder.ADMIN_USERNAME)
            if admin is None:
                raise RuntimeError("UserRepository could not find admin")

        await manager.dispose()
        print("OK")

    def run_cli(self) -> None:
        try:
            asyncio.run(self.verify())
        except Exception as exc:
            print(f"Verification failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    DatabaseVerifier().run_cli()
