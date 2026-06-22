from datetime import date, timedelta

from server.core.week_utils import WeekCalculator


class WorkingDayCalendar:
    @staticmethod
    def is_working_day(day: date) -> bool:
        return day.weekday() < 5

    @staticmethod
    def next_working_day_after(day: date) -> date:
        candidate = day + timedelta(days=1)
        while not WorkingDayCalendar.is_working_day(candidate):
            candidate += timedelta(days=1)
        return candidate

    @staticmethod
    def submission_deadline(week_start: date) -> date:
        WeekCalculator.validate_monday(week_start)
        return WeekCalculator.week_end(week_start)

    @staticmethod
    def reminder_1_day(week_start: date) -> date:
        return WorkingDayCalendar.next_working_day_after(
            WorkingDayCalendar.submission_deadline(week_start)
        )

    @staticmethod
    def reminder_2_day(week_start: date) -> date:
        return WorkingDayCalendar.next_working_day_after(
            WorkingDayCalendar.reminder_1_day(week_start)
        )

    @staticmethod
    def freeze_day(week_start: date) -> date:
        return WorkingDayCalendar.next_working_day_after(
            WorkingDayCalendar.reminder_2_day(week_start)
        )
