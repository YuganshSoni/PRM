from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from server.models.enums import UserStatus


class DeactivateUserScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("DEACTIVATE USER")
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

        status_label = (
            "Active" if user.status == UserStatus.ACTIVE else "Inactive"
        )
        print(f"User found: {user.full_name} ({user.role})")
        print(f"Status     : {status_label}")
        print()
        print("Are you sure you want to deactivate this account?")
        print("Deactivated users cannot log in. Their data is preserved.")
        print()
        print("[Y] Yes, Deactivate     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "Y":
            self._renderer.render_error(
                "Invalid option. Enter Y to deactivate or B to go back."
            )
            return ScreenResult.RETRY

        if user.status == UserStatus.INACTIVE:
            self._renderer.render_error("User is already inactive.")
            return ScreenResult.RETRY

        try:
            await self._client.deactivate_user(user.id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("User deactivated. ✓")
        return ScreenResult.BACK
