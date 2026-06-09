from datetime import datetime

from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.manager.resource_dashboard_screen import ResourceDashboardScreen
from client.screens.screen_result import ScreenResult


class ManagerMenu(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            session = self._session_manager.current
            full_name = session.full_name if session else "Manager"
            now = datetime.now().strftime("%d-%m-%Y  %H:%M")

            self._renderer.render_banner(
                "MANAGER PANEL",
                f"Welcome, {full_name}  |  {now}",
            )
            print("1. Resource Dashboard")
            print("2. Allocate Resource")
            print("3. My Projects")
            print("4. Timesheets")
            print("5. AI Assistant")
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
                dash_result = await ResourceDashboardScreen(*screen_args).run()
                if dash_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return dash_result
            case "2":
                self._renderer.render_message("Allocate Resource — coming in Phase 9.")
                return ScreenResult.RETRY
            case "3":
                self._renderer.render_message("My Projects — coming in Phase 13.")
                return ScreenResult.RETRY
            case "4":
                self._renderer.render_message("Timesheets — coming in Phase 11.")
                return ScreenResult.RETRY
            case "5":
                self._renderer.render_message("AI Assistant — coming in Phase 15.")
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
