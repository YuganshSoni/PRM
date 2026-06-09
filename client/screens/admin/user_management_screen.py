from client.screens.admin.create_user_screen import CreateUserScreen
from client.screens.admin.deactivate_user_screen import DeactivateUserScreen
from client.screens.admin.reset_password_screen import ResetPasswordScreen
from client.screens.admin.view_users_screen import ViewUsersScreen
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class UserManagementScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("MANAGE USERS")
            print("1. Create User Account")
            print("2. View All Users")
            print("3. Reset User Password")
            print("4. Deactivate User")
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
                return await CreateUserScreen(*screen_args).run()
            case "2":
                return await ViewUsersScreen(*screen_args).run()
            case "3":
                return await ResetPasswordScreen(*screen_args).run()
            case "4":
                return await DeactivateUserScreen(*screen_args).run()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–5.")
                return ScreenResult.RETRY
