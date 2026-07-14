from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from server.models.enums import UserStatus


class ViewUsersScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("ALL USERS")
        print()

        try:
            user_list = await self._client.list_users()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print(f"{'ID':<6}{'Username':<18}{'Role':<12}{'Status'}")
        print("─" * 46)
        for user in user_list.items:
            status_label = (
                "Active" if user.status == UserStatus.ACTIVE else "Inactive"
            )
            print(
                f"{user.id:<6}{user.username:<18}{user.role:<12}{status_label}"
            )
        print("─" * 46)
        print(
            f"Total: {user_list.total}   |   "
            f"Active: {user_list.active_count}   |   "
            f"Inactive: {user_list.inactive_count}"
        )
        print()
        print("[R] Reactivate a user     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "R":
            self._renderer.render_error("Invalid option. Enter R to reactivate or B to go back.")
            return ScreenResult.RETRY

        return await self._reactivate_user()

    async def _reactivate_user(self) -> ScreenResult:
        user_id_str = self._reader.read_line("Enter User ID to reactivate: ")
        if not user_id_str.isdigit():
            self._renderer.render_error("Please enter a valid numeric user ID.")
            return ScreenResult.RETRY

        user_id = int(user_id_str)
        try:
            user = await self._client.lookup_user(str(user_id))
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        if user.status == UserStatus.ACTIVE:
            self._renderer.render_error("User is already active.")
            return ScreenResult.RETRY

        status_label = "Inactive"
        print()
        print(f"User: {user.full_name} ({user.role}) — currently {status_label}")
        print()
        print("Reactivate this account?")
        print("[Y] Yes     [B] Cancel")
        print()

        confirm = self._reader.read_option("Enter option: ").upper()
        if confirm == "B":
            return ScreenResult.RETRY
        if confirm != "Y":
            self._renderer.render_error("Invalid option. Enter Y to confirm or B to cancel.")
            return ScreenResult.RETRY

        try:
            await self._client.reactivate_user(user_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(
            f"Account reactivated. {user.full_name} can now log in. ✓"
        )
        self._renderer.render_message(
            "Note: Previous allocations are NOT restored. "
            "Admin must re-allocate manually if needed."
        )
        self._renderer.render_message(
            "If the employee profile was deactivated via Manage Employees, "
            "also use Reactivate Resource to restore workforce access."
        )
        return ScreenResult.RETRY
