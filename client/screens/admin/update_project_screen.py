from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser
from server.models.enums import ProjectStatus


class UpdateProjectScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("UPDATE PROJECT DETAILS")
        print()

        project_id_str = self._reader.read_line("Enter Project ID: ")
        if not project_id_str.isdigit():
            self._renderer.render_error("Project ID must be a number.")
            return ScreenResult.RETRY

        project_id = int(project_id_str)
        try:
            project = await self._client.get_project(project_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print(f"── {project.name} ───────────────────────────────")
        name = self._reader.read_line(
            f"Project Name         : {project.name}          "
        ) or project.name
        description = self._reader.read_line(
            f"Description          : {project.description or ''}          "
        ) or project.description
        start_default = DateInputParser.format(project.start_date)
        end_default = DateInputParser.format(project.end_date)
        start_input = self._reader.read_line(
            f"Start Date           : {start_default}             "
        ) or start_default
        end_input = self._reader.read_line(
            f"End Date             : {end_default}             "
        ) or end_default
        print(
            "Status               : (1) PLANNED   (2) ACTIVE   "
            "(3) ON_HOLD   (4) COMPLETED"
        )
        status_choice = self._reader.read_line(
            f"Enter choice         : {self._status_number(project.status)}"
        ) or self._status_number(project.status)
        manager_id_str = self._reader.read_line(
            f"Assign Manager       : {project.manager_id}             "
        ) or str(project.manager_id)
        total_sp_str = self._reader.read_line(
            f"Total Story Points   : {project.total_story_points}                   "
        ) or str(project.total_story_points)
        print("─" * 46)
        print("[S] Save     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option != "S":
            self._renderer.render_error("Invalid option. Enter S to save or B to go back.")
            return ScreenResult.RETRY

        status = self._parse_update_status(status_choice)
        if status is None:
            self._renderer.render_error("Invalid status choice. Enter 1–4.")
            return ScreenResult.RETRY

        if not manager_id_str.isdigit():
            self._renderer.render_error("Manager ID must be a number.")
            return ScreenResult.RETRY

        if not total_sp_str.isdigit():
            self._renderer.render_error("Total story points must be a number.")
            return ScreenResult.RETRY

        try:
            start_date = DateInputParser.parse(start_input)
            end_date = DateInputParser.parse(end_input)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        try:
            await self._client.update_project(
                project_id,
                name=name,
                description=description or None,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                status=status.value,
                manager_id=int(manager_id_str),
                total_story_points=int(total_sp_str),
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("Project updated. ✓")
        return ScreenResult.BACK

    def _status_number(self, status: str) -> str:
        match status:
            case ProjectStatus.PLANNED:
                return "1"
            case ProjectStatus.ACTIVE:
                return "2"
            case ProjectStatus.ON_HOLD:
                return "3"
            case ProjectStatus.COMPLETED:
                return "4"
            case _:
                return "1"

    def _parse_update_status(self, choice: str) -> ProjectStatus | None:
        match choice.strip():
            case "1":
                return ProjectStatus.PLANNED
            case "2":
                return ProjectStatus.ACTIVE
            case "3":
                return ProjectStatus.ON_HOLD
            case "4":
                return ProjectStatus.COMPLETED
            case _:
                return None
