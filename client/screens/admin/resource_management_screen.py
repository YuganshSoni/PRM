from client.screens.admin.assign_manager_screen import AssignManagerScreen
from client.screens.admin.deactivate_resource_screen import DeactivateResourceScreen
from client.screens.admin.manage_skills_screen import ManageSkillsScreen
from client.screens.admin.update_resource_screen import UpdateResourceScreen
from client.screens.admin.view_resources_screen import ViewResourcesScreen
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class ResourceManagementScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("MANAGE EMPLOYEES")
            print("1. View All Resources")
            print("2. Update Resource")
            print("3. Deactivate Resource")
            print("4. Manage Resource Skills")
            print("5. Assign Manager")
            print("6. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            if option == "6":
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
                return await ViewResourcesScreen(*screen_args).run()
            case "2":
                return await UpdateResourceScreen(*screen_args).run()
            case "3":
                return await DeactivateResourceScreen(*screen_args).run()
            case "4":
                return await ManageSkillsScreen(*screen_args).run()
            case "5":
                return await AssignManagerScreen(*screen_args).run()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–6.")
                return ScreenResult.RETRY
