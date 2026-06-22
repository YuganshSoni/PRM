from client.exceptions import InvalidInputError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult


class StartScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_banner(
            "PROJECT & RESOURCE MANAGEMENT TOOL",
            "Learn & Code — Final Project",
        )
        print("1. Login")
        print("2. Exit")
        print()

        try:
            option = self._reader.read_option("Enter option: ")
            if option == "1":
                return ScreenResult.LOGIN
            if option == "2":
                return ScreenResult.EXIT
            raise InvalidInputError("Invalid option. Please enter 1 or 2.")
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
