from datetime import date
from decimal import Decimal

from clients.cbr import CbrSeriesPoint
from services.chart.caption import ChartSeriesSummary, format_chart_caption, format_price


def _pt(day: int, rate: str) -> CbrSeriesPoint:
    return CbrSeriesPoint(
        date=date(2026, 10, day),
        nominal=1,
        value=Decimal(rate),
        unit_rate=Decimal(rate),
    )


def _summary(code: str, name: str, points: list[CbrSeriesPoint]) -> ChartSeriesSummary:
    from services.chart.series import analyze_series

    extremes = analyze_series(points)
    assert extremes is not None
    return ChartSeriesSummary(code=code, name=name, extremes=extremes)


def test_format_price_is_bold():
    point = CbrSeriesPoint(
        date=date(2026, 10, 9),
        nominal=1,
        value=Decimal("85.4173"),
        unit_rate=Decimal("85.4173"),
    )
    assert format_price(point) == "<b>85.42</b> ₽"


def test_format_chart_caption_includes_disclaimer_and_extremes():
    summary = _summary("USD", "Доллар США", [_pt(1, "80"), _pt(2, "90"), _pt(3, "85")])
    text = format_chart_caption(
        period_label="Неделя",
        date_from=date(2026, 10, 3),
        date_to=date(2026, 10, 9),
        series=[summary],
        missing=[],
    )
    assert "Курсы ЦБ: Неделя (<b>03.10.2026 - 09.10.2026</b>)" in text
    assert "<b>Неделя</b>" not in text
    assert "🇺🇸 USD (за 1) - посл. <b>85.00</b> ₽ (03.10.2026)" in text
    assert "мин. <b>80.00</b> ₽ (01.10.2026)" in text
    assert "макс. <b>90.00</b> ₽ (02.10.2026)" in text
    assert "—" not in text
    assert "не цена" in text
    assert len(text) <= 1024


def test_format_chart_caption_flat():
    summary = _summary("EUR", "Евро", [_pt(1, "100"), _pt(2, "100")])
    text = format_chart_caption(
        period_label="Месяц",
        date_from=date(2026, 9, 10),
        date_to=date(2026, 10, 9),
        series=[summary],
        missing=[],
    )
    assert "EUR (за 1) - курс за период не менялся" in text
    assert "<b>100.00</b> ₽" in text
    assert "—" not in text


def test_format_chart_caption_missing():
    text = format_chart_caption(
        period_label="Неделя",
        date_from=date(2026, 10, 3),
        date_to=date(2026, 10, 9),
        series=[],
        missing=["XYZ"],
    )
    assert "Не найдены в фиде ЦБ: XYZ" in text


def test_format_chart_caption_truncates_many_currencies():
    series = [
        _summary(f"C{i:02d}", f"Валюта {i}", [_pt(1, str(50 + i)), _pt(2, str(60 + i))])
        for i in range(25)
    ]
    text = format_chart_caption(
        period_label="Полгода",
        date_from=date(2026, 4, 11),
        date_to=date(2026, 10, 9),
        series=series,
        missing=[],
    )
    assert len(text) <= 1024
    assert "не цена" in text
