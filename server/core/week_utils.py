from datetime import date, timedelta

from server.core.exceptions import FutureWeekError, InvalidWeekStartError


class WeekCalculator:
    @staticmethod
    def week_end(week_start: date) -> date:
        WeekCalculator.validate_monday(week_start)
        return week_start + timedelta(days=6)

    @staticmethod
    def current_week_monday(today: date) -> date:
        return today - timedelta(days=today.weekday())

    @staticmethod
    def prior_week_monday(today: date) -> date:
        return WeekCalculator.current_week_monday(today) - timedelta(days=7)

    @staticmethod
    def default_submit_week_start(today: date) -> date:
        return WeekCalculator.current_week_monday(today)

    @staticmethod
    def validate_monday(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise InvalidWeekStartError("Week start must be a Monday")

    @staticmethod
    def ensure_not_future(week_start: date, today: date) -> None:
        current_week = WeekCalculator.current_week_monday(today)
        if week_start > current_week:
            raise FutureWeekError("Cannot submit timesheet for a future week")
