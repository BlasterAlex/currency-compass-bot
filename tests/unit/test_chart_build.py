from datetime import date
from decimal import Decimal

import pytest

from bot.handlers.chart import _invalid, _parse_weeks
from bot.metrics import chart_builds_total, chart_errors_total, chart_series_missing_total
from clients.cbr import CbrDailyRates, CbrRate, CbrSeriesPoint
from db.models import Currency
from services.chart.build import build_chart


def _counter(metric, **labels) -> float:
    return metric.labels(**labels)._value.get()


def _currency() -> Currency:
    return Currency(code="USD", name="Доллар США")


def _daily() -> CbrDailyRates:
    return CbrDailyRates(
        date="09.10.2026",
        rates={
            "USD": CbrRate(
                code="USD",
                name="Доллар США",
                nominal=1,
                value=Decimal("80.00"),
                cbr_id="R01235",
            )
        },
    )


def _points() -> list[CbrSeriesPoint]:
    return [
        CbrSeriesPoint(date(2026, 10, 1), 1, Decimal("80.00"), Decimal("80.00")),
        CbrSeriesPoint(date(2026, 10, 2), 1, Decimal("90.00"), Decimal("90.00")),
    ]


@pytest.mark.asyncio
async def test_invalid_span_records_error():
    class _Callback:
        async def answer(self) -> None:
            return None

    before = _counter(chart_errors_total, reason="invalid_span")
    assert _parse_weeks("100") is None
    assert _parse_weeks("nope") is None
    await _invalid(_Callback())  # type: ignore[arg-type]
    assert _counter(chart_errors_total, reason="invalid_span") == before + 1


@pytest.mark.asyncio
async def test_build_chart_counts_success_period(monkeypatch):
    async def daily():
        return _daily()

    async def dynamic(cbr_id, date_from, date_to):
        return _points()

    monkeypatch.setattr("services.chart.build.get_daily_rates", daily)
    monkeypatch.setattr("services.chart.build.get_dynamic_rates", dynamic)
    monkeypatch.setattr("services.chart.build.render_chart_png", lambda *args, **kwargs: b"png")

    before = _counter(chart_builds_total, period="custom")
    result = await build_chart([_currency()], 2)
    assert result is not None
    assert result.weeks == 2
    assert "2 недели" in result.caption
    assert _counter(chart_builds_total, period="custom") == before + 1


@pytest.mark.asyncio
async def test_build_chart_no_data(monkeypatch):
    async def daily():
        return CbrDailyRates(date="09.10.2026", rates={})

    monkeypatch.setattr("services.chart.build.get_daily_rates", daily)
    before_errors = _counter(chart_errors_total, reason="no_data")
    before_builds = _counter(chart_builds_total, period="week")
    before_missing = chart_series_missing_total._value.get()

    assert await build_chart([_currency()], 1) is None
    assert _counter(chart_errors_total, reason="no_data") == before_errors + 1
    assert _counter(chart_builds_total, period="week") == before_builds
    assert chart_series_missing_total._value.get() == before_missing + 1


@pytest.mark.asyncio
async def test_build_chart_cbr_error(monkeypatch):
    async def daily():
        raise RuntimeError("cbr down")

    monkeypatch.setattr("services.chart.build.get_daily_rates", daily)
    before = _counter(chart_errors_total, reason="cbr")
    with pytest.raises(RuntimeError):
        await build_chart([_currency()], 1)
    assert _counter(chart_errors_total, reason="cbr") == before + 1


@pytest.mark.asyncio
async def test_build_chart_render_error(monkeypatch):
    async def daily():
        return _daily()

    async def dynamic(cbr_id, date_from, date_to):
        return _points()

    def render(*args, **kwargs):
        raise RuntimeError("render")

    monkeypatch.setattr("services.chart.build.get_daily_rates", daily)
    monkeypatch.setattr("services.chart.build.get_dynamic_rates", dynamic)
    monkeypatch.setattr("services.chart.build.render_chart_png", render)
    before = _counter(chart_errors_total, reason="render")
    before_builds = _counter(chart_builds_total, period="week")
    with pytest.raises(RuntimeError):
        await build_chart([_currency()], 1)
    assert _counter(chart_errors_total, reason="render") == before + 1
    assert _counter(chart_builds_total, period="week") == before_builds
