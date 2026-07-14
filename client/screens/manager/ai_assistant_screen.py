from client.context.ai_context_store import AiContextStore
from client.context.ai_flow_context import AiFlowContext
from client.exceptions import ApiRequestError, NetworkError
from client.schemas.ai import SkillMatchCandidateResponse, SkillMatchResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.ai_display_helper import AiDisplayHelper
from client.utils.ai_error_mapper import AiErrorMapper
from client.utils.health_display import HealthDisplayHelper


class AIAssistantScreen(BaseScreen):
    _MIN_REQUIREMENT_LENGTH = 10

    def __init__(
        self,
        client,
        session_manager,
        navigation,
        renderer,
        reader,
        *,
        ai_context_store: AiContextStore,
    ) -> None:
        super().__init__(client, session_manager, navigation, renderer, reader)
        self._ai_context_store = ai_context_store

    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("AI ASSISTANT")
            print()
            print("1. Skill Match    — Find best employees for a project requirement")
            print("2. Risk Summary   — Get a health analysis for a project")
            print("3. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            match option:
                case "1":
                    result = await self._skill_match_flow()
                    if result != ScreenResult.RETRY:
                        return result
                case "2":
                    result = await self._risk_summary_flow()
                    if result == ScreenResult.BACK:
                        continue
                    if result != ScreenResult.RETRY:
                        return result
                case "3":
                    return ScreenResult.BACK
                case _:
                    self._renderer.render_error("Invalid option. Please enter 1–3.")

    async def _skill_match_flow(self) -> ScreenResult:
        self._renderer.render_box_title("SKILL MATCH")
        print()
        print("Describe your project requirement in plain English:")
        requirement = self._reader.read_line("> ").strip()
        if len(requirement) < self._MIN_REQUIREMENT_LENGTH:
            self._renderer.render_error(
                f"Requirement must be at least {self._MIN_REQUIREMENT_LENGTH} characters."
            )
            return ScreenResult.RETRY

        AiDisplayHelper.render_searching_message()
        try:
            response = await self._client.skill_match(requirement=requirement)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        if not response.items:
            AiDisplayHelper.render_empty_skill_match(response)
            return ScreenResult.RETRY

        print()
        print("Results:")
        AiDisplayHelper.render_skill_match_results(
            response,
            disclaimer=AiDisplayHelper.ASSISTANT_DISCLAIMER,
        )

        selected = await self._optional_candidate_selection(response)

        while True:
            print("[A] Go to Allocate Resource     [B] Back")
            action = self._reader.read_line("Enter action: ").strip().upper()
            if action == "B":
                return ScreenResult.RETRY
            if action == "A":
                context = AiFlowContext(
                    requirement=requirement,
                    selected_resource_id=(
                        selected.resource_id if selected else None
                    ),
                    suggested_utilisation_percent=(
                        selected.suggested_utilisation_percent if selected else None
                    ),
                )
                self._ai_context_store.set(context)
                return ScreenResult.GO_ALLOCATE
            self._renderer.render_error("Invalid action. Enter A or B.")

    async def _optional_candidate_selection(
        self, response: SkillMatchResponse
    ) -> SkillMatchCandidateResponse | None:
        choice_raw = self._reader.read_line(
            "Optional — enter # to pre-select a candidate (or press Enter): "
        ).strip()
        if not choice_raw:
            return None
        if not choice_raw.isdigit():
            return None

        choice = int(choice_raw)
        candidate = next(
            (item for item in response.items if item.rank == choice),
            None,
        )
        if candidate is None:
            candidate = next(
                (
                    item
                    for index, item in enumerate(response.items, start=1)
                    if index == choice
                ),
                None,
            )
        return candidate

    async def _risk_summary_flow(self) -> ScreenResult:
        self._renderer.render_box_title("RISK SUMMARY")
        print()

        try:
            listing = await self._client.list_managed_projects()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        if not listing.items:
            self._renderer.render_error("No projects assigned.")
            return ScreenResult.RETRY

        print("Select project:")
        for index, project in enumerate(listing.items, start=1):
            health = HealthDisplayHelper.format_short(project.health_status)
            print(f"  {index}.  {project.name:<20} {health}")
        print()

        choice_raw = self._reader.read_line("Enter project number: ").strip()
        try:
            index = int(choice_raw)
        except ValueError:
            self._renderer.render_error("Enter a valid project number.")
            return ScreenResult.RETRY

        if index < 1 or index > len(listing.items):
            self._renderer.render_error("Invalid project number.")
            return ScreenResult.RETRY

        project = listing.items[index - 1]
        print()
        print("Generating AI summary...")

        try:
            summary = await self._client.risk_summary(project.id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return ScreenResult.RETRY

        AiDisplayHelper.render_risk_summary(summary)

        while True:
            action = self._reader.read_line("[B] Back — Enter B: ").strip().upper()
            if action == "B":
                return ScreenResult.RETRY
            self._renderer.render_error("Enter B to go back.")
