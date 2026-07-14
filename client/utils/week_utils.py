from datetime import date, timedelta


class WeekInputHelper:
    @staticmethod
    def default_week_start(today: date | None = None) -> date:
        reference = today or date.today()
        return reference - timedelta(days=reference.weekday())
