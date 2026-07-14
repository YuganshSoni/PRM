from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.schemas.allocation import BulkCreateAllocationRequest, BulkAllocationItemRequest
from client.schemas.team_build import TeamBuildResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.ai_error_mapper import AiErrorMapper
from client.utils.date_parser import DateInputParser
from client.utils.team_build_display_helper import TeamBuildDisplayHelper


class TeamBuilderScreen(BaseScreen):
    _MIN_REQUIREMENT_LENGTH = 10

    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("BUILD PROJECT TEAM (AI)")
            print()

            project_id = await self._pick_project_id()
            if project_id is None:
                return ScreenResult.BACK

            requirement = self._read_requirement()
            if requirement is None:
                continue

            response = await self._fetch_team_build(project_id, requirement)
            if response is None:
                continue

            TeamBuildDisplayHelper.render_results(response)

            if not response.matches:
                retry = self._reader.read_line(
                    "Enter 0 to search again, or B to go back: "
                ).strip()
                if retry.upper() == "B":
                    return ScreenResult.BACK
                if retry != "0":
                    self._renderer.render_error("Enter 0 to search again or B to go back.")
                continue

            result = await self._confirm_bulk_allocate(project_id, response)
            if result == ScreenResult.RETRY:
                continue
            return result

    async def _pick_project_id(self) -> int | None:
        try:
            projects = await self._client.list_managed_projects()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return None

        if not projects.items:
            self._renderer.render_error("You have no projects to staff.")
            return None

        print("Select a project:")
        for index, project in enumerate(projects.items, start=1):
            print(f"  {index}. {project.name} ({project.status})")
        print("  B. Back")
        print()

        while True:
            choice = self._reader.read_option("Enter option: ").strip()
            if choice.upper() == "B":
                return None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(projects.items):
                    return projects.items[index - 1].id
            self._renderer.render_error("Invalid option.")

    def _read_requirement(self) -> str | None:
        print()
        print("Describe the whole team you need in one paragraph:")
        print("(e.g. banking portal needs Senior Java Developer, DevOps, QA Tester)")
        requirement = self._reader.read_line("> ").strip()
        if len(requirement) < self._MIN_REQUIREMENT_LENGTH:
            self._renderer.render_error(
                f"Requirement must be at least {self._MIN_REQUIREMENT_LENGTH} characters."
            )
            return None
        return requirement

    async def _fetch_team_build(
        self, project_id: int, requirement: str
    ) -> TeamBuildResponse | None:
        TeamBuildDisplayHelper.render_searching_message()
        try:
            return await self._client.team_build(
                requirement=requirement,
                project_id=project_id,
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return None

    async def _confirm_bulk_allocate(
        self, project_id: int, response: TeamBuildResponse
    ) -> ScreenResult:
        print()
        print("Set allocation for all matched roles:")
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
        print("[C] Confirm bulk allocation     [B] Back")
        print()
        confirm = self._reader.read_option("Enter option: ").upper()
        if confirm == "B":
            return ScreenResult.RETRY
        if confirm != "C":
            self._renderer.render_error(
                "Invalid option. Enter C to confirm or B to go back."
            )
            return ScreenResult.RETRY

        payload = BulkCreateAllocationRequest(
            project_id=project_id,
            utilisation_percent=utilisation_percent,
            from_date=from_date,
            to_date=to_date,
            items=[
                BulkAllocationItemRequest(
                    resource_id=match.resource_id,
                    role_key=match.role_key,
                )
                for match in response.matches
            ],
        )

        try:
            result = await self._client.bulk_create_allocations(payload)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        print()
        self._renderer.render_message(
            f"Allocated {len(result.items)} team member(s) to {result.project_name}."
        )
        for item in result.items:
            print(
                f"  - {item.employee_name}: {item.utilisation_percent}% "
                f"({item.from_date} to {item.to_date})"
            )
        print()
        return ScreenResult.BACK
