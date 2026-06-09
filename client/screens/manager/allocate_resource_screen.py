from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class AllocateResourceScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("ALLOCATE RESOURCE")
            print()
            print("1. Find resource using AI (recommended)")
            print("2. Allocate directly (I already know who I want)")
            print("3. End an existing allocation")
            print("4. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            match option:
                case "1":
                    self._renderer.render_message(
                        "AI-assisted search — coming in Phase 15."
                    )
                case "2":
                    result = await self._direct_allocation_flow()
                    if result == ScreenResult.BACK:
                        continue
                    return result
                case "3":
                    result = await self._end_allocation_flow()
                    if result == ScreenResult.BACK:
                        continue
                    return result
                case "4":
                    return ScreenResult.BACK
                case _:
                    self._renderer.render_error("Invalid option. Please enter 1–4.")

    async def _pick_project_id(self) -> int | None:
        try:
            projects = await self._client.list_managed_projects()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return None

        if not projects.items:
            self._renderer.render_error("You have no managed projects.")
            return None

        print("Your projects:")
        for index, project in enumerate(projects.items, start=1):
            print(f"  {index}. {project.name} ({project.id}) — {project.status}")
        print()

        choice = self._reader.read_line(
            "Select project (number or ID): "
        ).strip()
        if not choice:
            self._renderer.render_error("Project selection is required.")
            return None

        if choice.isdigit():
            value = int(choice)
            by_index = next(
                (project for i, project in enumerate(projects.items, start=1) if i == value),
                None,
            )
            if by_index is not None:
                return by_index.id
            by_id = next(
                (project for project in projects.items if project.id == value),
                None,
            )
            if by_id is not None:
                return by_id.id

        self._renderer.render_error("Invalid project selection.")
        return None

    async def _direct_allocation_flow(self) -> ScreenResult:
        self._renderer.render_box_title("DIRECT ALLOCATION")
        print()

        project_id = await self._pick_project_id()
        if project_id is None:
            return ScreenResult.RETRY

        employee_id_raw = self._reader.read_line("Enter Employee ID: ").strip()
        if not employee_id_raw.isdigit():
            self._renderer.render_error("Employee ID must be a number.")
            return ScreenResult.RETRY

        employee_id = int(employee_id_raw)
        try:
            detail = await self._client.get_employee_detail(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print(f"── {detail.full_name} ─────────────────────────────────")
        print(
            f"Current Utilisation: {detail.utilisation_percent}%   "
            f"({'fully on bench' if detail.utilisation_percent == 0 else 'allocated'})"
        )
        print()

        utilisation_raw = self._reader.read_line("Utilisation %: ").strip()
        if not utilisation_raw.isdigit() or not 1 <= int(utilisation_raw) <= 100:
            self._renderer.render_error("Utilisation must be between 1 and 100.")
            return ScreenResult.RETRY
        utilisation_percent = int(utilisation_raw)

        try:
            from_date = DateInputParser.parse(
                self._reader.read_line("From Date (DD-MM-YYYY): ")
            )
            to_date = DateInputParser.parse(
                self._reader.read_line("To Date (DD-MM-YYYY): ")
            )
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print("[C] Confirm     [B] Back")
        print()
        confirm = self._reader.read_option("Enter option: ").upper()
        if confirm == "B":
            return ScreenResult.RETRY
        if confirm != "C":
            self._renderer.render_error("Invalid option. Enter C to confirm or B to go back.")
            return ScreenResult.RETRY

        try:
            result = await self._client.create_allocation(
                employee_id=employee_id,
                project_id=project_id,
                utilisation_percent=utilisation_percent,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(
            f"Allocation saved. {result.employee_name} → {result.project_name} "
            f"({result.utilisation_percent}%, "
            f"{DateInputParser.format(result.from_date)}–"
            f"{DateInputParser.format(result.to_date)}) ✓"
        )
        return ScreenResult.RETRY

    async def _end_allocation_flow(self) -> ScreenResult:
        self._renderer.render_box_title("END ALLOCATION")
        print()

        project_id = await self._pick_project_id()
        if project_id is None:
            return ScreenResult.RETRY

        try:
            allocation_list = await self._client.list_project_allocations(project_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        if not allocation_list.items:
            self._renderer.render_error("No active allocations on this project.")
            return ScreenResult.RETRY

        print(f"Active Allocations on {allocation_list.project_name}:")
        print(f"  {'#':<4}{'Employee':<16}{'%':<6}{'From':<12}{'To'}")
        for index, allocation in enumerate(allocation_list.items, start=1):
            from_date = DateInputParser.format(allocation.from_date)
            to_date = DateInputParser.format(allocation.to_date)
            print(
                f"  {index}. {allocation.employee_name:<14}"
                f"{allocation.utilisation_percent}%{'':<4}"
                f"{from_date:<12}{to_date}"
            )
        print()

        choice_raw = self._reader.read_line("Select allocation to end: ").strip()
        if not choice_raw.isdigit():
            self._renderer.render_error("Enter a valid allocation number.")
            return ScreenResult.RETRY

        choice = int(choice_raw)
        if choice < 1 or choice > len(allocation_list.items):
            self._renderer.render_error("Invalid allocation selection.")
            return ScreenResult.RETRY

        selected = allocation_list.items[choice - 1]
        print()
        print(
            f"End {selected.employee_name}'s allocation on "
            f"{allocation_list.project_name}?"
        )
        print("Set end date to today?")
        print()
        print("[Y] Yes, End Now    [B] Back")
        print()

        confirm = self._reader.read_option("Enter option: ").upper()
        if confirm == "B":
            return ScreenResult.RETRY
        if confirm != "Y":
            self._renderer.render_error("Invalid option. Enter Y to confirm or B to go back.")
            return ScreenResult.RETRY

        try:
            result = await self._client.end_allocation(selected.id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(
            f"Allocation ended. {result.employee_name} freed from "
            f"{result.project_name} as of "
            f"{DateInputParser.format(result.end_date)}. ✓"
        )
        return ScreenResult.RETRY
