from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class LoginScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        print("Login")
        print()

        username = self._reader.read_line("Username: ")
        password = self._reader.read_password("Password: ")

        if not username or not password:
            self._renderer.render_error("Username and password are required.")
            return ScreenResult.RETRY

        try:
            response = await self._client.login(username, password)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.START
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            self._session_manager.clear_session()
            return ScreenResult.START

        if response.force_password_change:
            return ScreenResult.CHANGE_PASSWORD
        return ScreenResult.MENU
