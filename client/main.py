import asyncio

from client.api.httpx_client import HttpxClient
from client.config import get_client_settings
from client.factories.screen_factory import ScreenFactory
from client.navigation import NavigationStack
from client.screens.change_password_screen import ChangePasswordScreen
from client.screens.login_screen import LoginScreen
from client.screens.screen_result import ScreenResult
from client.screens.start_screen import StartScreen
from client.session import SessionManager
from client.ui.console_reader import ConsoleReader
from client.ui.console_renderer import ConsoleRenderer


class Application:
    def __init__(self) -> None:
        self._settings = get_client_settings()
        self._session_manager = SessionManager()
        self._navigation = NavigationStack()
        self._renderer = ConsoleRenderer()
        self._reader = ConsoleReader()
        self._client = HttpxClient(self._settings, self._session_manager)
        self._screen_factory = ScreenFactory(
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )

    def _screen_args(self) -> tuple:
        return (
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )

    async def run(self) -> None:
        while True:
            start_result = await StartScreen(*self._screen_args()).run()

            if start_result == ScreenResult.EXIT:
                break
            if start_result == ScreenResult.RETRY:
                continue
            if start_result != ScreenResult.LOGIN:
                continue

            post_login = await self._run_login_flow()
            if post_login == ScreenResult.EXIT:
                break

    async def _run_login_flow(self) -> ScreenResult:
        while True:
            login_result = await LoginScreen(*self._screen_args()).run()

            if login_result == ScreenResult.RETRY:
                continue
            if login_result == ScreenResult.START:
                return ScreenResult.START

            if login_result == ScreenResult.CHANGE_PASSWORD:
                change_result = await self._run_change_password_flow()
                if change_result in (ScreenResult.START, ScreenResult.LOGOUT):
                    return ScreenResult.START
                if change_result == ScreenResult.RETRY:
                    continue
                login_result = ScreenResult.MENU

            if login_result == ScreenResult.MENU:
                menu_result = await self._run_role_menu()
                if menu_result == ScreenResult.LOGOUT:
                    return ScreenResult.START
                if menu_result == ScreenResult.EXIT:
                    return ScreenResult.EXIT
                if menu_result == ScreenResult.RETRY:
                    continue

            return ScreenResult.START

    async def _run_change_password_flow(self) -> ScreenResult:
        while True:
            result = await ChangePasswordScreen(*self._screen_args()).run()
            if result != ScreenResult.RETRY:
                return result

    async def _run_role_menu(self) -> ScreenResult:
        role = self._session_manager.get_role()
        menu = self._screen_factory.create_menu_for_role(role)
        while True:
            result = await menu.run()
            if result != ScreenResult.RETRY:
                return result


def main() -> None:
    asyncio.run(Application().run())


if __name__ == "__main__":
    main()
