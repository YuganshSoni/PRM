from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class ReactivateResourceScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("REACTIVATE RESOURCE")
        print()

        identifier_str = self._reader.read_line("Enter Resource ID or User ID: ")
        if not identifier_str.isdigit():
            self._renderer.render_error("ID must be a number.")
            return ScreenResult.RETRY

        identifier = int(identifier_str)
        resource = await self._load_resource(identifier)
        if resource is None:
            return ScreenResult.RETRY

        print()
        print(f"── {resource.full_name} ─────────────────────────────────")
        print(f"Department : {resource.department}")
        print(f"Status     : {resource.status}")
        print(
            f"Resource   : {'Active' if resource.is_active else 'Inactive (deactivated)'}"
        )
        print()

        if resource.is_active:
            self._renderer.render_error("Resource is already active.")
            return ScreenResult.RETRY

        print(f"Reactivate {resource.full_name}?")
        print("This will: restore the employee profile and set status to BENCH.")
        print("Login access is unchanged — use Manage Users to reactivate login if needed.")
        print("Note: Previous allocations are NOT restored.")
        print()
        print("[Y] Yes, Reactivate     [B] Cancel")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "Y":
            self._renderer.render_error("Invalid option. Enter Y to confirm or B to cancel.")
            return ScreenResult.RETRY

        try:
            result = await self._client.reactivate_employee(resource.id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(f"{result.message} ✓")
        return ScreenResult.BACK

    async def _load_resource(self, identifier: int):
        try:
            return await self._client.get_employee(identifier)
        except ApiRequestError as first_exc:
            if first_exc.status_code != 404:
                self._renderer.render_error(first_exc.message)
                return None
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None

        try:
            return await self._client.get_employee_by_user(identifier)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return None
