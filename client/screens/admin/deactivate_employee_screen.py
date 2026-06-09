from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class DeactivateEmployeeScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("DEACTIVATE EMPLOYEE")
        print()

        employee_id_str = self._reader.read_line("Enter Employee ID: ")
        if not employee_id_str.isdigit():
            self._renderer.render_error("Employee ID must be a number.")
            return ScreenResult.RETRY

        employee_id = int(employee_id_str)
        try:
            employee = await self._client.get_employee(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print(f"── {employee.full_name} ─────────────────────────────────")
        print(f"Department : {employee.department}")
        print(f"Status     : {employee.status}")
        print()

        if employee.active_allocations:
            count = len(employee.active_allocations)
            print(f"⚠  Warning: This employee has {count} active allocation(s).")
            print("   Ending their employment will remove them from:")
            for allocation in employee.active_allocations:
                end = allocation.to_date.strftime("%d-%b-%y")
                print(
                    f"     - {allocation.project_name}  "
                    f"({allocation.utilisation_percent}%,  ends {end})"
                )
            print()

        print(f"Are you sure you want to deactivate {employee.full_name}?")
        print("This will: set is_active = false, end all active allocations today,")
        print("and block their login account.")
        print()
        print("[Y] Yes, Deactivate     [B] Cancel")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "Y":
            self._renderer.render_error("Invalid option. Enter Y to confirm or B to cancel.")
            return ScreenResult.RETRY

        try:
            await self._client.deactivate_employee(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("Employee deactivated. ✓")
        return ScreenResult.BACK
