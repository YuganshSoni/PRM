from datetime import timedelta

from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.schemas.timesheet import TeamTimesheetRowResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser
from client.utils.week_utils import WeekInputHelper


class TimesheetsViewScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("TIMESHEETS — MY TEAM")
            print()
            print(
                "Filter by week (DD-MM-YYYY) or press Enter for current week:"
            )
            week_input = self._reader.read_line("Week: ").strip()

            try:
                week_start = self._resolve_week_start(week_input)
            except InvalidInputError as exc:
                self._renderer.render_error(exc.message)
                continue

            try:
                listing = await self._client.list_team_timesheets(
                    week_start=week_start.isoformat()
                )
            except NetworkError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY
            except ApiRequestError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY

            print()
            print("-" * 60)
            print(f"{'Employee':<18} {'Project':<18} {'Hrs':>6}  {'Status':<12}")
            print("-" * 60)

            if not listing.items:
                self._renderer.render_message("No team timesheets for this week.")
            else:
                for index, row in enumerate(listing.items, start=1):
                    status = row.status
                    if status == "MISSED":
                        status = f"{status}  ⚠"
                    print(
                        f"{row.resource_name:<18} {row.project_name:<18} "
                        f"{row.hours:>6}  {status:<12}  (#{index})"
                    )

            print("-" * 60)
            print()
            print("[V] View employee timesheet detail     [B] Back")
            action = self._reader.read_line("Enter action: ").strip().upper()

            if action == "B":
                return ScreenResult.BACK
            if action == "V":
                detail_result = await self._view_detail(listing.items)
                if detail_result == ScreenResult.BACK:
                    continue
                return detail_result
            self._renderer.render_error("Invalid action. Enter V or B.")

    def _resolve_week_start(self, raw: str):
        if not raw:
            return WeekInputHelper.default_week_start()
        parsed = DateInputParser.parse(raw)
        return parsed - timedelta(days=parsed.weekday())

    async def _view_detail(self, items: list[TeamTimesheetRowResponse]) -> ScreenResult:
        if not items:
            self._renderer.render_error("No rows to view.")
            return ScreenResult.RETRY

        choice = self._reader.read_line(
            "Enter row number or timesheet id: "
        ).strip()
        if not choice.isdigit():
            self._renderer.render_error("Enter a valid row number or timesheet id.")
            return ScreenResult.RETRY

        value = int(choice)
        by_index = next(
            (item for index, item in enumerate(items, start=1) if index == value),
            None,
        )
        selected = by_index
        if selected is None:
            selected = next(
                (item for item in items if item.timesheet_id == value),
                None,
            )

        if selected is None:
            self._renderer.render_error("Row or timesheet id not found in list.")
            return ScreenResult.RETRY

        if selected.timesheet_id is None or selected.status == "MISSED":
            self._renderer.render_message("No submission for this week.")
            self._reader.read_line("Press Enter to continue...")
            return ScreenResult.RETRY

        try:
            detail = await self._client.get_timesheet_detail(selected.timesheet_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
        print(f"Employee: {selected.resource_name}")
        print(f"Week: {DateInputParser.format(detail.week_start)}")
        print(f"Status: {detail.status}")
        print(f"Total hours: {detail.total_hours}")
        print()
        print(f"{'Project':<24} {'Hours':>8}  Tags")
        print("-" * 60)
        for entry in detail.entries:
            tags = ", ".join(entry.activity_tags)
            print(f"{entry.project_name:<24} {entry.hours:>8}  {tags}")
        print()
        self._reader.read_line("Press Enter to continue...")
        return ScreenResult.RETRY
