from datetime import date

import pytest

from server.core.exceptions import FutureWeekError, InvalidWeekStartError
from server.core.week_utils import WeekCalculator


def test_week_end_returns_sunday_for_monday_start():
    assert WeekCalculator.week_end(date(2026, 7, 13)) == date(2026, 7, 19)


def test_week_end_rejects_non_monday():
    with pytest.raises(InvalidWeekStartError, match="must be a Monday"):
        WeekCalculator.week_end(date(2026, 7, 14))


def test_current_week_monday_from_midweek():
    assert WeekCalculator.current_week_monday(date(2026, 7, 16)) == date(2026, 7, 13)


def test_current_week_monday_when_today_is_monday():
    assert WeekCalculator.current_week_monday(date(2026, 7, 13)) == date(2026, 7, 13)


def test_current_week_monday_when_today_is_sunday():
    assert WeekCalculator.current_week_monday(date(2026, 7, 19)) == date(2026, 7, 13)


def test_prior_week_monday():
    assert WeekCalculator.prior_week_monday(date(2026, 7, 16)) == date(2026, 7, 6)


def test_default_submit_week_start_is_current_monday():
    today = date(2026, 7, 15)
    assert WeekCalculator.default_submit_week_start(today) == date(2026, 7, 13)


def test_validate_monday_accepts_monday():
    WeekCalculator.validate_monday(date(2026, 7, 13))


def test_validate_monday_rejects_other_days():
    with pytest.raises(InvalidWeekStartError, match="must be a Monday"):
        WeekCalculator.validate_monday(date(2026, 7, 14))


def test_ensure_not_future_allows_current_week():
    today = date(2026, 7, 16)
    WeekCalculator.ensure_not_future(date(2026, 7, 13), today)


def test_ensure_not_future_allows_past_week():
    today = date(2026, 7, 16)
    WeekCalculator.ensure_not_future(date(2026, 7, 6), today)


def test_ensure_not_future_rejects_future_week():
    today = date(2026, 7, 16)
    with pytest.raises(FutureWeekError, match="future week"):
        WeekCalculator.ensure_not_future(date(2026, 7, 20), today)
