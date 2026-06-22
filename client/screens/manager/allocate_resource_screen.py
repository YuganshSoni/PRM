from datetime import date

from client.context.ai_flow_context import AiFlowContext
from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.schemas.ai import SkillMatchCandidateResponse, SkillMatchResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.ai_display_helper import AiDisplayHelper
from client.utils.ai_error_mapper import AiErrorMapper
from client.utils.date_parser import DateInputParser


class AllocateResourceScreen(BaseScreen):
    _MIN_REQUIREMENT_LENGTH = 10

    def __init__(
        self,
        client,
        session_manager,
        navigation,
        renderer,
        reader,
        *,
        initial_context: AiFlowContext | None = None,
    ) -> None:
        super().__init__(client, session_manager, navigation, renderer, reader)
        self._initial_context = initial_context

    async def run(self) -> ScreenResult:
        if self._initial_context is not None:
            result = await self._ai_assisted_search_flow(self._initial_context)
            if result != ScreenResult.RETRY:
                return result

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
                    result = await self._ai_assisted_search_flow()
                    if result == ScreenResult.BACK:
                        continue
                    if result != ScreenResult.RETRY:
                        return result
                case "2":
                    result = await self._direct_allocation_flow()
                    if result == ScreenResult.BACK:
                        continue
                    if result != ScreenResult.RETRY:
                        return result
                case "3":
                    result = await self._end_allocation_flow()
                    if result == ScreenResult.BACK:
                        continue
                    if result != ScreenResult.RETRY:
                        return result
                case "4":
                    return ScreenResult.BACK
                case _:
                    self._renderer.render_error("Invalid option. Please enter 1–4.")

    async def _pick_project_id(
        self, preselected_id: int | None = None
    ) -> int | None:
        if preselected_id is not None:
            return preselected_id

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
                (
                    project
                    for i, project in enumerate(projects.items, start=1)
                    if i == value
                ),
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

    async def _ai_assisted_search_flow(
        self, context: AiFlowContext | None = None
    ) -> ScreenResult:
        self._renderer.render_box_title("ALLOCATE RESOURCE")
        print()
        print("Step 1 — Select Project")

        project_id = await self._pick_project_id(
            context.project_id if context else None
        )
        if project_id is None:
            return ScreenResult.RETRY

        while True:
            print()
            print("Step 2 — Describe your requirement")
            print("Type what kind of resource you need:")
            if context and context.requirement:
                print(f"(Previous: {context.requirement})")
            requirement = self._read_requirement(context.requirement if context else None)
            if requirement is None:
                return ScreenResult.RETRY

            match_response = await self._fetch_skill_match(project_id, requirement)
            if match_response is None:
                return ScreenResult.RETRY

            if not match_response.items:
                AiDisplayHelper.render_empty_skill_match(match_response)
                retry = self._reader.read_line(
                    "Enter 0 to search again, or B to go back: "
                ).strip()
                if retry.upper() == "B":
                    return ScreenResult.RETRY
                if retry != "0":
                    self._renderer.render_error("Enter 0 to search again or B to go back.")
                context = None
                continue

            AiDisplayHelper.render_skill_match_results(match_response)

            preselected_id = context.selected_resource_id if context else None
            candidate = await self._select_candidate(
                match_response,
                preselected_id=preselected_id,
            )
            if candidate is None:
                context = None
                continue

            default_util = (
                candidate.suggested_utilisation_percent
                or (context.suggested_utilisation_percent if context else None)
            )
            result = await self._confirm_allocation_for_resource(
                resource_id=candidate.resource_id,
                resource_name=candidate.resource_name,
                project_id=project_id,
                default_utilisation_percent=default_util,
            )
            return result

    def _read_requirement(self, default: str | None) -> str | None:
        if default:
            use_default = self._reader.read_line(
                "Press Enter to reuse previous requirement, or type a new one:\n> "
            ).strip()
            if not use_default:
                if len(default.strip()) >= self._MIN_REQUIREMENT_LENGTH:
                    return default.strip()
                self._renderer.render_error(
                    f"Requirement must be at least {self._MIN_REQUIREMENT_LENGTH} characters."
                )
                return None
            requirement = use_default
        else:
            requirement = self._reader.read_line("> ").strip()

        if len(requirement) < self._MIN_REQUIREMENT_LENGTH:
            self._renderer.render_error(
                f"Requirement must be at least {self._MIN_REQUIREMENT_LENGTH} characters."
            )
            return None
        return requirement

    async def _fetch_skill_match(
        self, project_id: int, requirement: str
    ) -> SkillMatchResponse | None:
        AiDisplayHelper.render_searching_message()
        try:
            return await self._client.skill_match(
                requirement=requirement,
                project_id=project_id,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return None

    async def _select_candidate(
        self,
        response: SkillMatchResponse,
        *,
        preselected_id: int | None = None,
    ) -> SkillMatchCandidateResponse | None:
        if preselected_id is not None:
            match = next(
                (item for item in response.items if item.resource_id == preselected_id),
                None,
            )
            if match is not None:
                return match

        while True:
            choice_raw = self._reader.read_line(
                "Select employee (enter #, or 0 to search again): "
            ).strip()
            if choice_raw == "0":
                return None
            if not choice_raw.isdigit():
                self._renderer.render_error("Enter a valid number, 0 to search again.")
                continue

            choice = int(choice_raw)
            candidate = next(
                (item for item in response.items if item.rank == choice),
                None,
            )
            if candidate is None:
                by_index = next(
                    (
                        item
                        for index, item in enumerate(response.items, start=1)
                        if index == choice
                    ),
                    None,
                )
                candidate = by_index

            if candidate is None:
                self._renderer.render_error("Invalid selection.")
                continue
            return candidate

    async def _confirm_allocation_for_resource(
        self,
        *,
        resource_id: int,
        resource_name: str,
        project_id: int,
        default_utilisation_percent: int | None = None,
    ) -> ScreenResult:
        try:
            detail = await self._client.get_employee_detail(resource_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        print()
        print(f"── {detail.full_name} ─────────────────────────────────")
        bench_label = (
            "fully on bench" if detail.utilisation_percent == 0 else "allocated"
        )
        print(
            f"Current Utilisation: {detail.utilisation_percent}%   ({bench_label})"
        )
        print()
        print("Set Allocation:")

        if default_utilisation_percent is not None:
            utilisation_raw = self._reader.read_line(
                f"  Utilisation %   : [{default_utilisation_percent}] "
            ).strip()
            if not utilisation_raw:
                utilisation_percent = default_utilisation_percent
            elif utilisation_raw.isdigit() and 1 <= int(utilisation_raw) <= 100:
                utilisation_percent = int(utilisation_raw)
            else:
                self._renderer.render_error("Utilisation must be between 1 and 100.")
                return ScreenResult.RETRY
        else:
            utilisation_raw = self._reader.read_line("  Utilisation %   : ").strip()
            if not utilisation_raw.isdigit() or not 1 <= int(utilisation_raw) <= 100:
                self._renderer.render_error("Utilisation must be between 1 and 100.")
                return ScreenResult.RETRY
            utilisation_percent = int(utilisation_raw)

        try:
            from_date = DateInputParser.parse(
                self._reader.read_line("  From Date       : ")
            )
            to_date = DateInputParser.parse(
                self._reader.read_line("  To Date         : ")
            )
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print("[C] Confirm Allocation     [B] Back")
        print()
        confirm = self._reader.read_option("Enter option: ").upper()
        if confirm == "B":
            return ScreenResult.RETRY
        if confirm != "C":
            self._renderer.render_error(
                "Invalid option. Enter C to confirm or B to go back."
            )
            return ScreenResult.RETRY

        return await self._submit_allocation(
            employee_id=resource_id,
            employee_name=resource_name,
            project_id=project_id,
            utilisation_percent=utilisation_percent,
            from_date=from_date,
            to_date=to_date,
        )

    async def _submit_allocation(
        self,
        *,
        employee_id: int,
        employee_name: str,
        project_id: int,
        utilisation_percent: int,
        from_date: date,
        to_date: date,
    ) -> ScreenResult:
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
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        self._renderer.render_message(
            f"Allocation saved. {result.employee_name} → {result.project_name} "
            f"({result.utilisation_percent}%, "
            f"{DateInputParser.format(result.from_date)}–"
            f"{DateInputParser.format(result.to_date)}) ✓"
        )
        return ScreenResult.RETRY

    async def _direct_allocation_flow(self) -> ScreenResult:
        self._renderer.render_box_title("DIRECT ALLOCATION")
        print()

        project_id = await self._pick_project_id()
        if project_id is None:
            return ScreenResult.RETRY

        employee_id_raw = self._reader.read_line("Enter Resource ID: ").strip()
        if not employee_id_raw.isdigit():
            self._renderer.render_error("Resource ID must be a number.")
            return ScreenResult.RETRY

        employee_id = int(employee_id_raw)
        try:
            detail = await self._client.get_employee_detail(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        return await self._confirm_allocation_for_resource(
            resource_id=employee_id,
            resource_name=detail.full_name,
            project_id=project_id,
        )

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
        print(f"  {'#':<4}{'Resource':<16}{'%':<6}{'From':<12}{'To'}")
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
            self._renderer.render_error(
                "Invalid option. Enter Y to confirm or B to go back."
            )
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
