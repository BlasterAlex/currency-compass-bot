from datetime import date
from decimal import Decimal

from clients.cbr import CbrSeriesPoint
from services.chart.series import analyze_series


def _pt(day: int, rate: str) -> CbrSeriesPoint:
    return CbrSeriesPoint(
        date=date(2026, 10, day),
        nominal=1,
        value=Decimal(rate),
        unit_rate=Decimal(rate),
    )


def test_analyze_empty():
    assert analyze_series([]) is None


def test_analyze_rising():
    extremes = analyze_series([_pt(1, "80"), _pt(2, "85"), _pt(3, "90")])
    assert extremes is not None
    assert extremes.trough.date == date(2026, 10, 1)
    assert extremes.peak.date == date(2026, 10, 3)
    assert extremes.last.date == date(2026, 10, 3)
    assert extremes.flat is False


def test_analyze_peak_tie_picks_later():
    extremes = analyze_series([_pt(1, "90"), _pt(2, "80"), _pt(3, "90")])
    assert extremes is not None
    assert extremes.peak.date == date(2026, 10, 3)
    assert extremes.trough.date == date(2026, 10, 2)


def test_analyze_flat():
    extremes = analyze_series([_pt(1, "85"), _pt(2, "85")])
    assert extremes is not None
    assert extremes.flat is True
    assert extremes.peak.date == date(2026, 10, 2)
    assert extremes.trough.date == date(2026, 10, 2)


def test_analyze_last_equals_peak():
    extremes = analyze_series([_pt(1, "80"), _pt(2, "90")])
    assert extremes is not None
    assert extremes.last.date == extremes.peak.date


