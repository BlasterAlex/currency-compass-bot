from datetime import date
from decimal import Decimal

from clients.cbr import CbrSeriesPoint
from services.chart.render import ChartPanel, render_chart_png, smooth_series
from services.chart.series import analyze_series


def _pt(day: int, rate: str) -> CbrSeriesPoint:
    return CbrSeriesPoint(
        date=date(2026, 10, day),
        nominal=1,
        value=Decimal(rate),
        unit_rate=Decimal(rate),
    )


def test_render_chart_png_non_empty():
    points = [_pt(1, "80"), _pt(2, "90"), _pt(3, "85")]
    extremes = analyze_series(points)
    assert extremes is not None
    png = render_chart_png(
        [ChartPanel(code="USD", name="Доллар США", points=points, extremes=extremes)],
        period_label="Неделя",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 3),
    )
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000


def test_smooth_series_passes_through_real_points():
    dates = [
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 5),
        date(2026, 10, 6),
        date(2026, 10, 7),
        date(2026, 10, 8),
        date(2026, 10, 9),
    ]
    values = [80.0, 91.0, 84.0, 88.0, 83.0, 90.0, 86.0]
    xs, ys = smooth_series(dates, values)
    hits = {
        x.date(): y
        for x, y in zip(xs, ys, strict=True)
        if x.hour == 0 and x.minute == 0 and x.second == 0 and x.microsecond == 0
    }
    assert hits == dict(zip(dates, values, strict=True))


def test_smooth_series_stays_within_extrema():
    dates = [date(2026, 10, day) for day in range(1, 6)]
    values = [80.0, 90.0, 82.0, 88.0, 84.0]
    xs, ys = smooth_series(dates, values)
    assert len(xs) > len(dates)
    assert ys[0] == values[0]
    assert ys[-1] == values[-1]
    assert min(ys) >= min(values) - 1e-6
    assert max(ys) <= max(values) + 1e-6


def test_render_chart_png_rejects_empty():
    try:
        render_chart_png(
            [],
            period_label="Неделя",
            date_from=date(2026, 10, 1),
            date_to=date(2026, 10, 3),
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError")
