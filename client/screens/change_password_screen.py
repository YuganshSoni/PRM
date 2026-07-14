from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.password_policy import ClientPasswordPolicy
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class ChangePasswordScreen(BaseScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._password_policy = ClientPasswordPolicy()

    async def run(self) -> ScreenResult:
        self._renderer.render_box_title(
            "CHANGE PASSWORD",
            "You must set a new password to continue.",
        )

        new_password = self._reader.read_password("New Password        : ")
        confirm_password = self._reader.read_password("Confirm Password    : ")
        print()
        self._renderer.render_divider()
        print("[S] Save and Continue     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()

        if option == "B":
            self.go_back()
            self._session_manager.clear_session()
            return ScreenResult.START

        if option != "S":
            self._renderer.render_error("Invalid option. Enter S to save or B to go back.")
            return ScreenResult.RETRY

        if new_password != confirm_password:
            self._renderer.render_error("Passwords do not match.")
            return ScreenResult.RETRY

        try:
            self._password_policy.validate(new_password)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        try:
            await self._client.change_password(new_password, confirm_password)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            if exc.code in ("WeakPasswordError", "PasswordMismatchError"):
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY
            if exc.code in ("InvalidTokenError", "TokenExpiredError"):
                self._session_manager.clear_session()
                self._renderer.render_error(exc.message)
                return ScreenResult.START
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("Password updated. Welcome! ✓")
        return ScreenResult.MENU
