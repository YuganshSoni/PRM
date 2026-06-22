from decimal import Decimal, InvalidOperation

from client.exceptions import ApiRequestError, InvalidInputError, NetworkError
from client.schemas.activity_tag import ActivityTagListResponse
from client.schemas.allocation import WeekAllocationContextResponse
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from client.utils.date_parser import DateInputParser
from client.utils.week_utils import WeekInputHelper


class SubmitTimesheetScreen(BaseScreen):
    async def run(self) -> ScreenResult:
        self._renderer.render_box_title("SUBMIT TIMESHEET")
        print()

        week_start = await self._prompt_week_start()
        if week_start is None:
            return ScreenResult.BACK

        week_context = await self._load_week_context(week_start)
        if week_context is None:
            return ScreenResult.RETRY
        if not week_context.projects:
            self._renderer.render_message("No allocations for this week.")
            print("[B] Back")
            action = self._reader.read_line("Enter action: ").strip().upper()
            return ScreenResult.BACK if action == "B" else ScreenResult.RETRY

        tags = await self._load_activity_tags()
        if tags is None:
            return ScreenResult.RETRY

        entries = await self._collect_entries(week_context, tags)
        if entries is None:
            return ScreenResult.RETRY

        total_hours = sum(entry["hours"] for entry in entries)
        self._render_summary(week_context, entries, total_hours)

        action = self._reader.read_line("Enter action ([S] Submit, [B] Back): ").strip().upper()
        if action == "B":
            return ScreenResult.BACK
        if action != "S":
            self._renderer.render_error("Invalid action. Enter S to submit or B to go back.")
            return ScreenResult.RETRY

        return await self._submit(week_start, entries)

    async def _prompt_week_start(self) -> str | None:
        raw = self._reader.read_line(
            "Enter week start (DD-MM-YYYY) or press Enter for current week Monday: "
        ).strip()
        if not raw:
            return WeekInputHelper.default_week_start().isoformat()

        try:
            parsed = DateInputParser.parse(raw)
        except InvalidInputError as exc:
            self._renderer.render_error(exc.message)
            return None
        return parsed.isoformat()

    async def _load_week_context(
        self, week_start: str
    ) -> WeekAllocationContextResponse | None:
        try:
            result = await self._client.list_my_allocations(week_start=week_start)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return None

        if not isinstance(result, WeekAllocationContextResponse):
            self._renderer.render_error("Unexpected response from server.")
            return None
        return result

    async def _load_activity_tags(self) -> ActivityTagListResponse | None:
        try:
            return await self._client.list_activity_tags()
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return None
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return None

    async def _collect_entries(
        self,
        week_context: WeekAllocationContextResponse,
        tags: ActivityTagListResponse,
    ) -> list[dict[str, object]] | None:
        ordered_tags = sorted(tags.items, key=lambda item: item.display_order)
        entries: list[dict[str, object]] = []
        total_projects = len(week_context.projects)

        for index, project in enumerate(week_context.projects, start=1):
            print()
            print(f"PROJECT {index} OF {total_projects}: {project.project_name}")
            print(
                f"Allocation: {project.utilisation_percent}%  "
                f"(max {project.max_hours:.2f} hrs)"
            )

            hours_raw = self._reader.read_line("Hours worked: ").strip()
            try:
                hours = Decimal(hours_raw)
                if hours < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                self._renderer.render_error("Hours must be a non-negative number.")
                return None

            self._print_tag_menu(ordered_tags)
            tag_input = self._reader.read_line(
                "Select tags (comma-separated numbers, e.g. 1,7): "
            ).strip()
            selected_tags = self._parse_tag_selection(tag_input, ordered_tags)
            if selected_tags is None:
                return None

            other_tag = next(
                (tag for tag in ordered_tags if tag.name == "Other"),
                None,
            )
            tag_payload: list[dict[str, object]] = []
            for tag in selected_tags:
                custom_label = None
                if other_tag is not None and tag.id == other_tag.id:
                    custom_label = self._reader.read_line(
                        "Enter custom label for Other: "
                    ).strip()
                    if not custom_label:
                        self._renderer.render_error(
                            "Custom label is required when selecting Other."
                        )
                        return None
                tag_payload.append(
                    {
                        "activity_tag_id": tag.id,
                        "custom_label": custom_label,
                    }
                )

            entries.append(
                {
                    "project_id": project.project_id,
                    "hours": float(hours),
                    "tags": tag_payload,
                }
            )

        return entries

    def _print_tag_menu(self, ordered_tags: list) -> None:
        print("Activity tags:")
        for tag in ordered_tags:
            print(f"  {tag.display_order}. {tag.name}")

    def _parse_tag_selection(
        self, raw: str, ordered_tags: list
    ) -> list | None:
        if not raw:
            self._renderer.render_error("Select at least one activity tag.")
            return None

        by_order = {tag.display_order: tag for tag in ordered_tags}
        selected = []
        for part in raw.split(","):
            token = part.strip()
            if not token.isdigit():
                self._renderer.render_error("Tag selection must be numbers 1–11.")
                return None
            order = int(token)
            tag = by_order.get(order)
            if tag is None:
                self._renderer.render_error(f"Invalid tag number: {order}")
                return None
            if tag not in selected:
                selected.append(tag)
        return selected

    def _render_summary(
        self,
        week_context: WeekAllocationContextResponse,
        entries: list[dict[str, object]],
        total_hours: Decimal,
    ) -> None:
        print()
        print("SUMMARY")
        print(f"Week start: {DateInputParser.format(week_context.week_start)}")
        print(f"{'Project':<24} {'Hours':>8}")
        print("-" * 34)
        project_names = {
            project.project_id: project.project_name
            for project in week_context.projects
        }
        for entry in entries:
            name = project_names.get(int(entry["project_id"]), "Unknown")
            print(f"{name:<24} {entry['hours']:>8}")
        print("-" * 34)
        print(
            f"Total: {total_hours} / {week_context.max_weekly_hours} hrs"
        )
        print()

    async def _submit(
        self, week_start: str, entries: list[dict[str, object]]
    ) -> ScreenResult:
        try:
            response = await self._client.submit_timesheet(
                {"week_start": week_start, "entries": entries}
            )
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message(response.message)
        return ScreenResult.BACK
