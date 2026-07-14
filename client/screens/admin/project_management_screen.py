from client.screens.admin.create_project_screen import CreateProjectScreen
from client.screens.admin.manage_milestones_screen import ManageMilestonesScreen
from client.screens.admin.update_project_screen import UpdateProjectScreen
from client.screens.admin.view_projects_screen import ViewProjectsScreen
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class ProjectManagementScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("MANAGE PROJECTS")
            print("1. Create Project")
            print("2. View All Projects")
            print("3. Update Project Details")
            print("4. Manage Milestones")
            print("5. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            if option == "5":
                return ScreenResult.BACK

            result = await self._dispatch_option(option)
            if result == ScreenResult.BACK:
                continue
            if result == ScreenResult.RETRY:
                continue
            return result

    async def _dispatch_option(self, option: str) -> ScreenResult:
        screen_args = (
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )
        match option:
            case "1":
                return await CreateProjectScreen(*screen_args).run()
            case "2":
                return await ViewProjectsScreen(*screen_args).run()
            case "3":
                return await UpdateProjectScreen(*screen_args).run()
            case "4":
                return await ManageMilestonesScreen(*screen_args).run()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–5.")
                return ScreenResult.RETRY
