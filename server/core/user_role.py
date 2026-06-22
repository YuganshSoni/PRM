from server.models.enums import UserRole
from server.models.user import User


def user_role_name(user: User) -> str:
    """Return role name; ``user.role`` must be eager-loaded (no lazy load in async)."""
    return user.role.name


def user_role_enum(user: User) -> UserRole:
    return UserRole(user_role_name(user))
