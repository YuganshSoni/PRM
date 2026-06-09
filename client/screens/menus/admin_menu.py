from datetime import datetime

from client.exceptions import ApiRequestError, NetworkError
from client.screens.admin.user_management_screen import UserManagementScreen
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class AdminMenu(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            session = self._session_manager.current
            full_name = session.full_name if session else "Admin"
            now = datetime.now().strftime("%d-%m-%Y  %H:%M")

            self._renderer.render_banner(
                "ADMIN PANEL",
                f"Welcome, {full_name}  |  {now}",
            )
            print("1. Manage Employees")
            print("2. Manage Projects")
            print("3. View All Allocations")
            print("4. Manage Users")
            print("5. System Configuration")
            print("6. Logout")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            result = await self._handle_option(option)
            if result != ScreenResult.RETRY:
                return result

    async def _handle_option(self, option: str) -> ScreenResult:
        screen_args = (
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )

        match option:
            case "1":
                self._renderer.render_message(
                    "Manage Employees — available in Phase 5."
                )
                return ScreenResult.RETRY
            case "2":
                self._renderer.render_message(
                    "Manage Projects — available in Phase 6."
                )
                return ScreenResult.RETRY
            case "3":
                self._renderer.render_message(
                    "View All Allocations — available in Phase 7."
                )
                return ScreenResult.RETRY
            case "4":
                um_result = await UserManagementScreen(*screen_args).run()
                if um_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return um_result
            case "5":
                self._renderer.render_message(
                    "System Configuration — available in Phase 7."
                )
                return ScreenResult.RETRY
            case "6":
                return await self._logout()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–6.")
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
