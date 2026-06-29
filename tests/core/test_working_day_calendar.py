from datetime import date

import pytest

from server.core.exceptions import InvalidWeekStartError
from server.core.working_day_calendar import WorkingDayCalendar


def test_is_working_day_true_for_weekdays():
    assert WorkingDayCalendar.is_working_day(date(2026, 7, 13)) is True  # Mon
    assert WorkingDayCalendar.is_working_day(date(2026, 7, 17)) is True  # Fri


def test_is_working_day_false_for_weekend():
    assert WorkingDayCalendar.is_working_day(date(2026, 7, 18)) is False  # Sat
    assert WorkingDayCalendar.is_working_day(date(2026, 7, 19)) is False  # Sun


def test_next_working_day_after_weekday():
    assert WorkingDayCalendar.next_working_day_after(date(2026, 7, 14)) == date(
        2026, 7, 15
    )


def test_next_working_day_after_friday_is_monday():
    assert WorkingDayCalendar.next_working_day_after(date(2026, 7, 17)) == date(
        2026, 7, 20
    )


def test_next_working_day_after_saturday_is_monday():
    assert WorkingDayCalendar.next_working_day_after(date(2026, 7, 18)) == date(
        2026, 7, 20
    )


def test_submission_deadline_is_week_end_sunday():
    assert WorkingDayCalendar.submission_deadline(date(2026, 7, 13)) == date(
        2026, 7, 19
    )


def test_submission_deadline_rejects_non_monday():
    with pytest.raises(InvalidWeekStartError):
        WorkingDayCalendar.submission_deadline(date(2026, 7, 14))


def test_reminder_1_day_is_first_working_day_after_sunday():
    # week ends Sunday 19th → next working day Monday 20th
    assert WorkingDayCalendar.reminder_1_day(date(2026, 7, 13)) == date(2026, 7, 20)


def test_reminder_2_day_is_working_day_after_reminder_1():
    assert WorkingDayCalendar.reminder_2_day(date(2026, 7, 13)) == date(2026, 7, 21)


def test_freeze_day_is_working_day_after_reminder_2():
    assert WorkingDayCalendar.freeze_day(date(2026, 7, 13)) == date(2026, 7, 22)
