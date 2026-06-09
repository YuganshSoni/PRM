from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.password_policy import ClientPasswordPolicy
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class ResetPasswordScreen(BaseScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._password_policy = ClientPasswordPolicy()

    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("RESET USER PASSWORD")
        print()

        identifier = self._reader.read_line("Enter Username or User ID: ")
        if not identifier:
            self._renderer.render_error("Username or User ID is required.")
            return ScreenResult.RETRY

        try:
            user = await self._client.lookup_user(identifier)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print(f"User found: {user.full_name} ({user.role})")
        print()
        new_password = self._reader.read_password("New Temporary Password: ")
        print()
        self._renderer.render_divider()
        print("[S] Save     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "S":
            self._renderer.render_error("Invalid option. Enter S to save or B to go back.")
            return ScreenResult.RETRY

        if not new_password:
            self._renderer.render_error("Password is required.")
            return ScreenResult.RETRY

        try:
            self._password_policy.validate(new_password)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        try:
            await self._client.reset_password(user.id, new_password)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(
            "Password reset. User will be prompted to change it on next login. ✓"
        )
        return ScreenResult.BACK
