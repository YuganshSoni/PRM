from datetime import datetime

from client.context.ai_context_store import AiContextStore
from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.manager.ai_assistant_screen import AIAssistantScreen
from client.screens.manager.allocate_resource_screen import AllocateResourceScreen
from client.screens.manager.my_projects_screen import MyProjectsScreen
from client.screens.manager.resource_dashboard_screen import ResourceDashboardScreen
from client.screens.manager.team_builder_screen import TeamBuilderScreen
from client.screens.manager.timesheets_view_screen import TimesheetsViewScreen
from client.screens.screen_result import ScreenResult


class ManagerMenu(BaseScreen):
    def __init__(
        self,
        client,
        session_manager,
        navigation,
        renderer,
        reader,
        *,
        ai_context_store: AiContextStore,
    ) -> None:
        super().__init__(client, session_manager, navigation, renderer, reader)
        self._ai_context_store = ai_context_store

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
            print("6. Build Project Team (AI)")
            print("7. Logout")
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
                context = self._ai_context_store.consume()
                alloc_result = await AllocateResourceScreen(
                    *screen_args,
                    initial_context=context,
                ).run()
                if alloc_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return alloc_result
            case "3":
                projects_result = await MyProjectsScreen(*screen_args).run()
                if projects_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return projects_result
            case "4":
                timesheets_result = await TimesheetsViewScreen(*screen_args).run()
                if timesheets_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return timesheets_result
            case "5":
                assist_result = await AIAssistantScreen(
                    *screen_args,
                    ai_context_store=self._ai_context_store,
                ).run()
                if assist_result == ScreenResult.GO_ALLOCATE:
                    return await self._open_allocate_from_assistant(screen_args)
                if assist_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return assist_result
            case "6":
                team_result = await TeamBuilderScreen(*screen_args).run()
                if team_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return team_result
            case "7":
                return await self._logout()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–7.")
                return ScreenResult.RETRY

    async def _open_allocate_from_assistant(
        self, screen_args: tuple
    ) -> ScreenResult:
        context = self._ai_context_store.consume()
        alloc_result = await AllocateResourceScreen(
            *screen_args,
            initial_context=context,
        ).run()
        if alloc_result == ScreenResult.BACK:
            return ScreenResult.RETRY
        return alloc_result

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
