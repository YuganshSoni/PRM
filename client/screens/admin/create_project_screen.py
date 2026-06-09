from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser
from server.models.enums import ProjectStatus


class CreateProjectScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("CREATE PROJECT")
        print()

        name = self._reader.read_line("Project Name        : ")
        description = self._reader.read_line("Description         : ")
        start_input = self._reader.read_line("Start Date          : (DD-MM-YYYY) ")
        end_input = self._reader.read_line("End Date            : (DD-MM-YYYY) ")
        print("Status              : (1) PLANNED   (2) ACTIVE   (3) ON_HOLD")
        status_choice = self._reader.read_line("Enter choice        : ")
        manager_id_str = self._reader.read_line("Assign Manager      : (Enter Manager ID) ")
        total_sp_str = self._reader.read_line("Total Story Points  : ")
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

        if not name:
            self._renderer.render_error("Project name is required.")
            return ScreenResult.RETRY

        status = self._parse_create_status(status_choice)
        if status is None:
            self._renderer.render_error("Invalid status choice. Enter 1, 2, or 3.")
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
            await self._client.create_project(
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

        self._renderer.render_message("Project created. ✓")
        return ScreenResult.BACK

    def _parse_create_status(self, choice: str) -> ProjectStatus | None:
        match choice.strip():
            case "1":
                return ProjectStatus.PLANNED
            case "2":
                return ProjectStatus.ACTIVE
            case "3":
                return ProjectStatus.ON_HOLD
            case _:
                return None
