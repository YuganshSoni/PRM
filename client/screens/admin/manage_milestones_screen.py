from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.schemas.milestone import MilestoneListResponse
from client.utils.date_parser import DateInputParser
from server.models.enums import MilestoneStatus


class ManageMilestonesScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("MILESTONES")
        print()

        project_id_str = self._reader.read_line("Enter Project ID: ")
        if not project_id_str.isdigit():
            self._renderer.render_error("Project ID must be a number.")
            return ScreenResult.RETRY

        self._project_id = int(project_id_str)
        try:
            project = await self._client.get_project(self._project_id)
            milestones = await self._client.list_project_milestones(self._project_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        while True:
            self._render_milestones(project.name, milestones)
            print("1. Add Milestone")
            print("2. Update Milestone Status")
            print("3. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            if option == "3":
                return ScreenResult.BACK
            if option == "1":
                milestones = await self._add_milestone(milestones)
                continue
            if option == "2":
                milestones = await self._update_status(milestones)
                continue
            self._renderer.render_error("Invalid option. Please enter 1–3.")

    def _render_milestones(
        self, project_name: str, milestones: MilestoneListResponse
    ) -> None:
        print()
        print(f"── {project_name} ───────────────────────────────")
        print(f"{'#':<5}{'Title':<20}{'Due Date':<12}{'Story Pts':<11}{'Status'}")
        print("─" * 58)
        if not milestones.items:
            print("  (none)")
        else:
            for index, milestone in enumerate(milestones.items, start=1):
                due = DateInputParser.format(milestone.due_date)
                print(
                    f"{index}.{'':<3}{milestone.title:<20}{due:<12}"
                    f"{milestone.story_points:<11}{milestone.status}"
                )
        summary = milestones.story_point_summary
        print("─" * 58)
        print(
            f"Total: {summary.total} SP   |   "
            f"Completed: {summary.completed} SP   |   "
            f"Remaining: {summary.remaining} SP"
        )

    async def _add_milestone(
        self, milestones: MilestoneListResponse
    ) -> MilestoneListResponse:
        title = self._reader.read_line("Milestone Title  : ")
        due_input = self._reader.read_line("Due Date         : (DD-MM-YYYY) ")
        sp_str = self._reader.read_line("Story Points     : ")

        if not title:
            self._renderer.render_error("Milestone title is required.")
            return milestones
        if not sp_str.isdigit() or int(sp_str) <= 0:
            self._renderer.render_error("Story points must be a positive number.")
            return milestones

        try:
            due_date = DateInputParser.parse(due_input)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return milestones

        try:
            await self._client.add_milestone(
                self._project_id,
                title=title,
                due_date=due_date.isoformat(),
                story_points=int(sp_str),
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return milestones
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return milestones

        self._renderer.render_message("Milestone added. ✓")
        return await self._client.list_project_milestones(self._project_id)

    async def _update_status(
        self, milestones: MilestoneListResponse
    ) -> MilestoneListResponse:
        if not milestones.items:
            self._renderer.render_error("No milestones to update.")
            return milestones

        index_str = self._reader.read_line("Enter Milestone # : ")
        if not index_str.isdigit():
            self._renderer.render_error("Enter a valid milestone number.")
            return milestones

        index = int(index_str) - 1
        if index < 0 or index >= len(milestones.items):
            self._renderer.render_error("Invalid milestone number.")
            return milestones

        print("New Status        : (1) NOT_STARTED   (2) IN_PROGRESS   (3) DONE")
        status_choice = self._reader.read_line("Enter choice      : ")
        status = self._parse_milestone_status(status_choice)
        if status is None:
            self._renderer.render_error("Invalid status choice. Enter 1–3.")
            return milestones

        milestone = milestones.items[index]
        try:
            await self._client.update_milestone_status(milestone.id, status.value)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return milestones
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return milestones

        self._renderer.render_message("Milestone updated. ✓")
        return await self._client.list_project_milestones(self._project_id)

    def _parse_milestone_status(self, choice: str) -> MilestoneStatus | None:
        match choice.strip():
            case "1":
                return MilestoneStatus.NOT_STARTED
            case "2":
                return MilestoneStatus.IN_PROGRESS
            case "3":
                return MilestoneStatus.DONE
            case _:
                return None
