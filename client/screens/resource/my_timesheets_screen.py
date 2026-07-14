from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class MyTimesheetsScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("MY TIMESHEETS")
            print()

            try:
                listing = await self._client.list_my_timesheets()
            except NetworkError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY
            except ApiRequestError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY

            if not listing.items:
                self._renderer.render_message("No timesheets found.")
            else:
                print(f"{'Week Start':<16} {'Total Hrs':>10} {'Status':<12}")
                print("-" * 40)
                for index, item in enumerate(listing.items, start=1):
                    week_label = DateInputParser.format(item.week_start)
                    status = item.status
                    if status == "MISSED":
                        status = f"{status}  ⚠"
                    print(
                        f"{week_label:<16} {str(item.total_hours) + ' hrs':>10} "
                        f"{status:<12}  (#{index}, id={item.id})"
                    )

            print()
            print("[V] View detail   [B] Back")
            action = self._reader.read_line("Enter action: ").strip().upper()

            if action == "B":
                return ScreenResult.BACK
            if action == "V":
                detail_result = await self._view_detail(listing.items)
                if detail_result == ScreenResult.BACK:
                    continue
                return detail_result
            self._renderer.render_error("Invalid action. Enter V or B.")

    async def _view_detail(self, items) -> ScreenResult:
        if not items:
            self._renderer.render_error("No timesheets to view.")
            return ScreenResult.RETRY

        choice = self._reader.read_line(
            "Enter timesheet id or row number: "
        ).strip()
        if not choice.isdigit():
            self._renderer.render_error("Enter a valid id or row number.")
            return ScreenResult.RETRY

        value = int(choice)
        by_index = next(
            (item for index, item in enumerate(items, start=1) if index == value),
            None,
        )
        timesheet_id = by_index.id if by_index is not None else value

        try:
            detail = await self._client.get_timesheet_detail(timesheet_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        print()
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
