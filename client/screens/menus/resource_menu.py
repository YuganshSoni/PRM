from datetime import datetime

from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.resource.my_allocations_screen import MyAllocationsScreen
from client.screens.resource.my_timesheets_screen import MyTimesheetsScreen
from client.screens.resource.submit_timesheet_screen import SubmitTimesheetScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class ResourceMenu(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            session = self._session_manager.current
            full_name = session.full_name if session else "Resource"
            now = datetime.now().strftime("%d-%m-%Y")

            self._renderer.render_banner(
                "EMPLOYEE PANEL",
                f"Welcome, {full_name}!  |  {now}",
            )

            await self._render_missed_reminder()

            print("1. Submit Timesheet")
            print("2. View My Timesheets")
            print("3. View My Allocations")
            print("4. Logout")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            result = await self._handle_option(option)
            if result != ScreenResult.RETRY:
                return result

    async def _render_missed_reminder(self) -> None:
        try:
            reminder = await self._client.get_missed_reminder()
        except (NetworkError, ApiRequestError):
            return

        if reminder.show_reminder and reminder.week_start is not None:
            week_label = DateInputParser.format(reminder.week_start)
            print(f"  ⚠  Reminder: Timesheet for week {week_label} has not been submitted.")
            print()

    async def _handle_option(self, option: str) -> ScreenResult:
        screen_args = (
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )

        match option:
            case "1":
                submit_result = await SubmitTimesheetScreen(*screen_args).run()
                if submit_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return submit_result
            case "2":
                history_result = await MyTimesheetsScreen(*screen_args).run()
                if history_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return history_result
            case "3":
                alloc_result = await MyAllocationsScreen(*screen_args).run()
                if alloc_result == ScreenResult.BACK:
                    return ScreenResult.RETRY
                return alloc_result
            case "4":
                return await self._logout()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–4.")
                return ScreenResult.RETRY

    async def _logout(self) -> ScreenResult:
        try:
            await self._client.logout()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            if exc.code in ("InvalidTokenError", "TokenExpiredError"):
                self._session_manager.clear_session()
                self._renderer.render_message("Session ended.")
                return ScreenResult.LOGOUT
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._session_manager.clear_session()
        self._renderer.render_message("Logged out successfully.")
        return ScreenResult.LOGOUT
