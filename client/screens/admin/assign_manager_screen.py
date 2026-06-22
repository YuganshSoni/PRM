from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class AssignManagerScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("ASSIGN MANAGER")
        print()

        employee_user_id = self._reader.read_line("Resource User ID : ")
        manager_user_id = self._reader.read_line("Manager User ID  : ")
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

        if not employee_user_id.isdigit() or not manager_user_id.isdigit():
            self._renderer.render_error("User IDs must be numeric.")
            return ScreenResult.RETRY

        try:
            await self._client.assign_manager(
                employee_user_id=int(employee_user_id),
                manager_user_id=int(manager_user_id),
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("Manager assigned successfully. ✓")
        return ScreenResult.BACK
