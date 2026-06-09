from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from server.models.enums import EmployeeStatus


class ViewEmployeesScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        return await self._render_list()

    async def _render_list(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
    ) -> ScreenResult:
        self._renderer.render_box_title("ALL EMPLOYEES")
        print()

        try:
            employee_list = await self._client.list_employees(
                status=status,
                department=department,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print(f"{'ID':<6}{'Name':<20}{'Department':<14}{'Status'}")
        print("─" * 50)
        for employee in employee_list.items:
            print(
                f"{employee.id:<6}{employee.full_name:<20}"
                f"{employee.department:<14}{employee.status}"
            )
        print("─" * 50)
        print(
            f"Total: {employee_list.total}   |   "
            f"Allocated: {employee_list.allocated_count}   |   "
            f"Bench: {employee_list.bench_count}"
        )
        print()
        print("[F] Filter by Status / Department     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option == "F":
            return await self._filter()
        self._renderer.render_error("Invalid option. Enter F to filter or B to go back.")
        return ScreenResult.RETRY

    async def _filter(self) -> ScreenResult:
        print("Leave blank to skip a filter.")
        status_input = self._reader.read_line("Status (BENCH/ALLOCATED): ").strip().upper()
        department = self._reader.read_line("Department: ").strip()

        status: str | None = None
        if status_input:
            if status_input not in (EmployeeStatus.BENCH, EmployeeStatus.ALLOCATED):
                self._renderer.render_error("Status must be BENCH or ALLOCATED.")
                return ScreenResult.RETRY
            status = status_input

        dept: str | None = department if department else None
        return await self._render_list(status=status, department=dept)
