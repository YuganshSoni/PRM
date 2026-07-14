from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.security import PasswordHasher
from server.models.enums import UserRole, UserStatus
from server.models.user import User
from server.seed.base_seeder import BaseSeeder


class BootstrapAdminSeeder(BaseSeeder):
    ADMIN_USERNAME = "admin"
    ADMIN_EMAIL = "admin@techserve.local"
    ADMIN_FULL_NAME = "System Admin"
    ADMIN_DEFAULT_PASSWORD = "Admin@1234"

    def __init__(self, password_hasher: PasswordHasher) -> None:
        self._password_hasher = password_hasher

    async def run(self, session: AsyncSession) -> None:
        result = await session.execute(
            select(User).where(User.username == self.ADMIN_USERNAME)
        )
        if result.scalar_one_or_none() is not None:
            return

        from server.models.role import Role
        role_result = await session.execute(
            select(Role).where(Role.name == UserRole.ADMIN.value)
        )
        admin_role = role_result.scalar_one_or_none()
        
        if not admin_role:
            raise RuntimeError("ADMIN role not found. Ensure LookupDataSeeder runs before BootstrapAdminSeeder.")

        session.add(
            User(
                username=self.ADMIN_USERNAME,
                email=self.ADMIN_EMAIL,
                full_name=self.ADMIN_FULL_NAME,
                password_hash=self._password_hasher.hash(self.ADMIN_DEFAULT_PASSWORD),
                role_id=admin_role.id,
                status=UserStatus.ACTIVE,
                force_password_change=True,
            )
        )
        await session.flush()
