from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser


class ResourceDashboardScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        return await self._render_dashboard()

    async def _render_dashboard(self) -> ScreenResult:
        try:
            dashboard = await self._client.get_resource_dashboard()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_box_title(
            f"RESOURCE DASHBOARD — {dashboard.month_label}"
        )
        print()

        bench_count = len(dashboard.bench_employees)
        print(f"ON BENCH  ({bench_count} resources available)")
        print("─" * 62)
        print(f"{'ID':<6}{'Name':<18}{'Department':<14}{'Skills'}")
        for resource in dashboard.bench_employees:
            skills = ", ".join(resource.skills)
            print(
                f"{resource.id:<6}{resource.full_name:<18}"
                f"{resource.department:<14}{skills}"
            )
        print()

        print("ACTIVE EMPLOYEES")
        print("─" * 62)
        print(f"{'ID':<6}{'Name':<18}{'Alloc %':<10}{'Availability'}")
        for resource in dashboard.active_employees:
            print(
                f"{resource.id:<6}{resource.full_name:<18}"
                f"{resource.utilisation_percent}%{'':<6}"
                f"{resource.availability_label}"
            )
        print()
        print("─" * 62)
        print(
            f"Bench: {dashboard.stats.bench_count}   |   "
            f"Partial: {dashboard.stats.partial_count}"
        )
        print()
        print("[D] Drill into resource details     [B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return ScreenResult.BACK
        if option == "D":
            return await self._drill_down()
        self._renderer.render_error("Invalid option. Enter D to drill down or B to go back.")
        return ScreenResult.RETRY

    async def _drill_down(self) -> ScreenResult:
        employee_id_raw = self._reader.read_line("Enter Resource ID: ").strip()
        if not employee_id_raw.isdigit():
            self._renderer.render_error("Resource ID must be a number.")
            return await self._render_dashboard()

        employee_id = int(employee_id_raw)
        try:
            detail = await self._client.get_employee_detail(employee_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return await self._render_dashboard()
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return await self._render_dashboard()

        print()
        print(f"── {detail.full_name} ─────────────────────────────────")
        print(f"Department     : {detail.department}")
        print(
            f"Current Status : {detail.status} ({detail.utilisation_percent}%)"
        )
        skills = ", ".join(detail.skills) if detail.skills else "(none)"
        print(f"Profile Skills : {skills}")
        print()
        print("Active Allocations:")
        if detail.active_allocations:
            print(f"  {'Project':<16}{'%':<6}{'From':<12}{'To'}")
            for allocation in detail.active_allocations:
                from_date = DateInputParser.format(allocation.from_date)
                to_date = DateInputParser.format(allocation.to_date)
                print(
                    f"  {allocation.project_name:<16}"
                    f"{allocation.utilisation_percent}%{'':<4}"
                    f"{from_date:<12}{to_date}"
                )
        else:
            print("  (none)")
        print()
        print("Recent Activity Tags (last 4 weeks):")
        if detail.recent_activity_tags:
            print(f"  {', '.join(detail.recent_activity_tags)}")
        else:
            print("  (none)")
        print()
        print("[B] Back")
        print()

        option = self._reader.read_option("Enter option: ").upper()
        if option == "B":
            return await self._render_dashboard()
        self._renderer.render_error("Invalid option. Enter B to go back.")
        return await self._render_dashboard()
