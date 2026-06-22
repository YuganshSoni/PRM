from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class UpdateResourceScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("UPDATE EMPLOYEE")
        print()

        user_id_str = self._reader.read_line("User ID       : ")
        if not user_id_str.isdigit():
            self._renderer.render_error("User ID must be a number.")
            return ScreenResult.RETRY

        full_name = self._reader.read_line("Full Name     : ")
        email = self._reader.read_line("Email         : ")
        department = self._reader.read_line("Department    : ")
        designation = self._reader.read_line("Designation   : ")
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

        if not all([full_name, email, department, designation]):
            self._renderer.render_error("All fields are required.")
            return ScreenResult.RETRY

        try:
            result = await self._client.update_employee_by_user(
                user_id=int(user_id_str),
                full_name=full_name,
                email=email,
                department=department,
                designation=designation,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        if result.created:
            self._renderer.render_message("Resource profile created (BENCH). ✓")
        else:
            self._renderer.render_message("Resource profile updated. ✓")
        return ScreenResult.BACK
