from client.exceptions import ApiRequestError, NetworkError
from client.schemas.project import ManagedProjectSummaryResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.ai_display_helper import AiDisplayHelper
from client.utils.ai_error_mapper import AiErrorMapper
from client.utils.health_display import HealthDisplayHelper


class MyProjectsScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        while True:
            self._renderer.render_box_title("MY PROJECTS")
            print()

            try:
                listing = await self._client.list_managed_projects()
            except NetworkError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY
            except ApiRequestError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY

            if not listing.items:
                self._renderer.render_message("No projects assigned.")
                print()
                print("[B] Back")
                action = self._reader.read_line("Enter action: ").strip().upper()
                if action == "B":
                    return ScreenResult.BACK
                self._renderer.render_error("Invalid action. Enter B to go back.")
                continue

            print(f"{'#':<4} {'Project':<20} {'End Date':<12} Health")
            print("-" * 60)
            for index, project in enumerate(listing.items, start=1):
                end_date = project.end_date.strftime("%d-%b-%y")
                health = HealthDisplayHelper.format_short(project.health_status)
                print(f"{index:<4} {project.name:<20} {end_date:<12} {health}")
            print("-" * 60)
            print()
            print("[B] Back")
            choice = self._reader.read_line(
                "Select project number to view details (or B): "
            ).strip()

            if choice.upper() == "B":
                return ScreenResult.BACK

            detail_result = await self._open_detail(listing.items, choice)
            if detail_result == ScreenResult.BACK:
                continue
            return detail_result

    async def _open_detail(
        self, items: list[ManagedProjectSummaryResponse], choice: str
    ) -> ScreenResult:
        try:
            index = int(choice)
        except ValueError:
            self._renderer.render_error("Enter a valid project number or B.")
            return ScreenResult.RETRY

        if index < 1 or index > len(items):
            self._renderer.render_error("Invalid project number.")
            return ScreenResult.RETRY

        project_id = items[index - 1].id

        try:
            detail = await self._client.get_manager_project_detail(project_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            if exc.code == "ProjectNotFoundError":
                self._renderer.render_error("Project not found.")
            else:
                self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        return await self._detail_loop(detail)

    async def _detail_loop(self, detail) -> ScreenResult:
        while True:
            print()
            print(f"── {detail.name} " + "─" * max(1, 45 - len(detail.name)))
            print(f"Health Status : {HealthDisplayHelper.format(detail.health_status)}")
            print()
            print("Risk Flags:")
            if not detail.risk_flags:
                print("  (none)")
            else:
                for flag in detail.risk_flags:
                    prefix = "✓" if flag.is_positive else "✗"
                    print(f"  {prefix}  {flag.flag_text}")

            print()
            print("Milestones:")
            print(f"  {'#':<4} {'Title':<18} {'Due Date':<12} Status")
            for index, milestone in enumerate(detail.milestones, start=1):
                due = milestone.due_date.strftime("%d-%b-%y")
                status = milestone.status.replace("_", " ")
                overdue = "  ⚠ OVERDUE" if milestone.is_overdue else ""
                print(
                    f"  {index:<4} {milestone.title:<18} {due:<12} "
                    f"{status}{overdue}"
                )

            print()
            print("Allocated Resources:")
            if not detail.allocations:
                print("  (none)")
            else:
                print(f"  {'Name':<16} {'%':<6} {'From':<12} To")
                for allocation in detail.allocations:
                    from_date = allocation.from_date.strftime("%d-%b-%y")
                    to_date = allocation.to_date.strftime("%d-%b-%y")
                    print(
                        f"  {allocation.resource_name:<16} "
                        f"{allocation.utilisation_percent}%{'':<4} "
                        f"{from_date:<12} {to_date}"
                    )

            print()
            print("-" * 60)
            print("[A] Get AI Risk Summary     [B] Back")
            action = self._reader.read_line("Enter action: ").strip().upper()

            if action == "B":
                return ScreenResult.BACK
            if action == "A":
                await self._show_ai_risk_summary(detail.id)
                continue
            self._renderer.render_error("Invalid action. Enter A or B.")

    async def _show_ai_risk_summary(self, project_id: int) -> None:
        print()
        print("Generating AI summary...")
        try:
            response = await self._client.risk_summary(project_id)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return
        except ApiRequestError as exc:
            self._renderer.render_error(AiErrorMapper.message_for(exc))
            return

        AiDisplayHelper.render_risk_summary(response)

        while True:
            back = self._reader.read_line("[B] Back — Enter B: ").strip().upper()
            if back == "B":
                return
            self._renderer.render_error("Enter B to go back.")
