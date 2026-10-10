from datetime import date

from services.chart.period import (
    LEGACY_WEEKS,
    is_allowed_weeks,
    metric_period,
    period_label,
    period_window,
    quick_button,
    weeks_for_pick,
)


def test_period_window_lengths():
    today = date(2026, 10, 9)
    assert period_window(1, today=today) == (date(2026, 10, 3), today)
    for weeks, days in ((1, 7), (4, 28), (24, 168), (48, 336)):
        start, end = period_window(weeks, today=today)
        assert end == today
        assert (end - start).days + 1 == days


def test_period_labels_collapse_equal_windows():
    assert period_label(1) == "Неделя"
    assert period_label(2) == "2 недели"
    assert period_label(5) == "5 недель"
    assert period_label(4) == "Месяц"
    assert period_label(8) == "2 месяца"
    assert period_label(12) == "3 месяца"
    assert period_label(20) == "5 месяцев"
    assert period_label(44) == "11 месяцев"
    assert period_label(24) == "Полгода"
    assert period_label(48) == "Год"
    assert period_label(96) == "2 года"
    assert period_label(240) == "5 лет"


def test_quick_button_follows_label():
    assert quick_button(1) == "week"
    assert quick_button(4) == "month"
    assert quick_button(24) == "half_year"
    assert quick_button(2) is None
    assert quick_button(8) is None
    assert quick_button(48) is None
    assert quick_button(96) is None


def test_weeks_for_pick_and_allowed_set():
    assert weeks_for_pick("week", 4) == 4
    assert weeks_for_pick("month", 6) == 24
    assert weeks_for_pick("month", 12) == 48
    assert weeks_for_pick("year", 2) == 96
    assert weeks_for_pick("week", 9) is None
    assert weeks_for_pick("year", 6) is None
    assert weeks_for_pick("day", 1) is None
    assert is_allowed_weeks(3)
    assert is_allowed_weeks(240)
    assert not is_allowed_weeks(100)
    assert not is_allowed_weeks(0)


def test_legacy_periods_match_quick_windows():
    assert LEGACY_WEEKS == {"week": 1, "month": 4, "half_year": 24}


def test_metric_period_buckets():
    assert metric_period(1) == "week"
    assert metric_period(4) == "month"
    assert metric_period(24) == "half_year"
    assert metric_period(48) == "year"
    assert metric_period(2) == "custom"
    assert metric_period(96) == "custom"
