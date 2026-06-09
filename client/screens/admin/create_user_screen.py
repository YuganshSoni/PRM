from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.password_policy import ClientPasswordPolicy
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from server.models.enums import UserRole


class CreateUserScreen(BaseScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._password_policy = ClientPasswordPolicy()

    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("CREATE USER ACCOUNT")
        print()

        full_name = self._reader.read_line("Full Name         : ")
        email = self._reader.read_line("Email             : ")
        username = self._reader.read_line("Username          : ")
        temporary_password = self._reader.read_password("Temporary Password: ")
        print("Role              : (1) Admin  (2) Manager  (3) Employee")
        role_option = self._reader.read_line("Select role [1-3]: ")
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

        if not all([full_name, email, username, temporary_password, role_option]):
            self._renderer.render_error("All fields are required.")
            return ScreenResult.RETRY

        role = self._parse_role(role_option)
        if role is None:
            self._renderer.render_error("Invalid role. Enter 1, 2, or 3.")
            return ScreenResult.RETRY

        try:
            self._password_policy.validate(temporary_password)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        try:
            await self._client.create_user(
                full_name=full_name,
                email=email,
                username=username,
                temporary_password=temporary_password,
                role=role.value,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(
            "Account created. User must change password on first login. ✓"
        )
        return ScreenResult.BACK

    def _parse_role(self, option: str) -> UserRole | None:
        match option.strip():
            case "1":
                return UserRole.ADMIN
            case "2":
                return UserRole.MANAGER
            case "3":
                return UserRole.EMPLOYEE
            case _:
                return None
