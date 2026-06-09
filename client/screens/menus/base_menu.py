from datetime import datetime

from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class BaseMenuScreen(BaseScreen):
    def __init__(self, role_label: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._role_label = role_label

    async def run(self) -> ScreenResult:
        session = self._session_manager.current
        full_name = session.full_name if session else "User"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._renderer.render_banner(
            f"{self._role_label} MENU",
            f"Welcome, {full_name}  |  {now}",
        )
        print("(Phase 4+ features not yet implemented)")
        print()
        print("[L] Logout")
        print()

        option = self._reader.read_option("Enter option: ").upper()

        if option == "L":
            return await self._logout()

        self._renderer.render_error(
            "Invalid option. Features coming in Phase 4+. Enter L to logout."
        )
        return ScreenResult.RETRY

    async def _logout(self) -> ScreenResult:
        try:
            await self._client.logout()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            if exc.code in ("InvalidTokenError", "TokenExpiredError"):
                self._session_manager.clear_session()
                self._renderer.render_message("Session ended.")
                return ScreenResult.LOGOUT
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._session_manager.clear_session()
        self._renderer.render_message("Logged out successfully.")
        return ScreenResult.LOGOUT
