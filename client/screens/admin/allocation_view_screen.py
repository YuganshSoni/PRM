from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class AllocationViewScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        return await self._render_list()

    async def _render_list(
        self,
        *,
        employee_id: int | None = None,
        project_id: int | None = None,
        employee_name: str | None = None,
        project_name: str | None = None,
    ) -> ScreenResult:
        self._renderer.render_box_title("ALL ALLOCATIONS")
        print()

        try:
            allocation_list = await self._client.list_allocations(
                employee_id=employee_id,
                project_id=project_id,
                employee_name=employee_name,
                project_name=project_name,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print(
            f"{'Resource':<18}{'Project':<18}{'%':<8}"
            f"{'From':<12}{'To'}"
        )
        print("─" * 62)
        for allocation in allocation_list.items:
            from_date = DateInputParser.format(allocation.from_date)
            to_date = DateInputParser.format(allocation.to_date)
            print(
                f"{allocation.employee_name:<18}{allocation.project_name:<18}"
                f"{allocation.utilisation_percent}%{'':<5}"
                f"{from_date:<12}{to_date}"
            )
        print("─" * 62)
        print(f"Total Active Allocations: {allocation_list.total}")
        print()
        print("[F] Filter by Resource / Project     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option == "F":
            return await self._filter()
        self._renderer.render_error("Invalid option. Enter F to filter or B to go back.")
        return ScreenResult.RETRY

    async def _filter(self) -> ScreenResult:
        print("Filter by (1) Resource  (2) Project")
        choice = self._reader.read_line("Enter choice: ").strip()
        if choice == "1":
            value = self._reader.read_line(
                "Enter resource name or ID: "
            ).strip()
            if not value:
                self._renderer.render_error("Filter value is required.")
                return ScreenResult.RETRY
            if value.isdigit():
                return await self._render_list(employee_id=int(value))
            return await self._render_list(employee_name=value)
        if choice == "2":
            value = self._reader.read_line("Enter project name or ID: ").strip()
            if not value:
                self._renderer.render_error("Filter value is required.")
                return ScreenResult.RETRY
            if value.isdigit():
                return await self._render_list(project_id=int(value))
            return await self._render_list(project_name=value)
        self._renderer.render_error("Invalid choice. Enter 1 or 2.")
        return ScreenResult.RETRY
