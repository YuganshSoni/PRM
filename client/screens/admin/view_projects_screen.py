from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class ViewProjectsScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("ALL PROJECTS")
        print()

        try:
            project_list = await self._client.list_projects()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print(
            f"{'ID':<6}{'Name':<18}{'Manager':<14}{'End Date':<12}"
            f"{'Status':<10}{'SP Done/Total'}"
        )
        print("─" * 72)
        for project in project_list.items:
            end_date = DateInputParser.format(project.end_date)
            sp_display = f"{project.story_points_done} / {project.story_points_total}"
            print(
                f"{project.id:<6}{project.name:<18}{project.manager_name:<14}"
                f"{end_date:<12}{project.status:<10}{sp_display}"
            )
        print("─" * 72)
        print()
        print("[B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        self._renderer.render_error("Invalid option. Enter B to go back.")
        return ScreenResult.RETRY
