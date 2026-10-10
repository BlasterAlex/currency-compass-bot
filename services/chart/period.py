from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Moscow has no DST since 2014.
_MSK = timezone(timedelta(hours=3))

WEEKS_IN_MONTH = 4
WEEKS_IN_YEAR = 48
HALF_YEAR_WEEKS = 24

LEGACY_WEEKS: dict[str, int] = {
    "week": 1,
    "month": WEEKS_IN_MONTH,
    "half_year": HALF_YEAR_WEEKS,
}

_UNIT_STEP = {"week": 1, "month": WEEKS_IN_MONTH, "year": WEEKS_IN_YEAR}
_UNIT_LIMIT = {"week": 8, "month": 12, "year": 5}

_ALLOWED_WEEKS = frozenset(
    list(range(1, 9))
    + [WEEKS_IN_MONTH * count for count in range(1, 13)]
    + [WEEKS_IN_YEAR * count for count in range(1, 6)]
)

_QUICK_BY_LABEL = {
    "Неделя": "week",
    "Месяц": "month",
    "Полгода": "half_year",
}


def is_allowed_weeks(weeks: int) -> bool:
    return weeks in _ALLOWED_WEEKS


def weeks_for_pick(unit: str, count: int) -> int | None:
    step = _UNIT_STEP.get(unit)
    limit = _UNIT_LIMIT.get(unit)
    if step is None or limit is None or not 1 <= count <= limit:
        return None
    weeks = step * count
    if weeks not in _ALLOWED_WEEKS:
        return None
    return weeks


def _plural(count: int, one: str, few: str, many: str) -> str:
    n = abs(count) % 100
    if 11 <= n <= 14:
        return many
    tail = n % 10
    if tail == 1:
        return one
    if 2 <= tail <= 4:
        return few
    return many


def period_label(weeks: int) -> str:
    """Canonical title for a week count. Number appears only above 1."""
    if weeks % WEEKS_IN_YEAR == 0:
        years = weeks // WEEKS_IN_YEAR
        if years == 1:
            return "Год"
        return f"{years} {_plural(years, 'год', 'года', 'лет')}"
    if weeks == HALF_YEAR_WEEKS:
        return "Полгода"
    if weeks % WEEKS_IN_MONTH == 0:
        months = weeks // WEEKS_IN_MONTH
        if months == 1:
            return "Месяц"
        return f"{months} {_plural(months, 'месяц', 'месяца', 'месяцев')}"
    if weeks == 1:
        return "Неделя"
    return f"{weeks} {_plural(weeks, 'неделя', 'недели', 'недель')}"


def quick_button(weeks: int) -> str | None:
    """Quick-row key when the label matches one, otherwise the custom button."""
    return _QUICK_BY_LABEL.get(period_label(weeks))


def metric_period(weeks: int) -> str:
    return {
        1: "week",
        WEEKS_IN_MONTH: "month",
        HALF_YEAR_WEEKS: "half_year",
        WEEKS_IN_YEAR: "year",
    }.get(weeks, "custom")


def _today_msk() -> date:
    return datetime.now(_MSK).date()


def period_window(weeks: int, *, today: date | None = None) -> tuple[date, date]:
    """Inclusive calendar window of `weeks` * 7 days ending on today (MSK)."""
    end = today if today is not None else _today_msk()
    start = end - timedelta(days=weeks * 7 - 1)
    return start, end
