from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class MyAllocationsScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("MY ALLOCATIONS")
        print()

        try:
            listing = await self._client.list_my_allocations()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        if not listing.items:
            self._renderer.render_message("No active allocations.")
        else:
            print(
                f"{'Project':<20} {'%':>4} {'From':<12} {'To':<12} {'Status':<8}"
            )
            print("-" * 60)
            for item in listing.items:
                print(
                    f"{item.project_name:<20} "
                    f"{item.utilisation_percent:>3}% "
                    f"{DateInputParser.format(item.from_date):<12} "
                    f"{DateInputParser.format(item.to_date):<12} "
                    f"{item.status:<8}"
                )
            print()
            print(f"Total Utilisation: {listing.total_utilisation_percent}%")

        print()
        self._reader.read_line("[B] Back — press Enter...")
        return ScreenResult.BACK
