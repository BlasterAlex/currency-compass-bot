from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from bot.metrics import (
    chart_builds_total,
    chart_errors_total,
    chart_render_duration_seconds,
    chart_series_missing_total,
)
from clients.cbr import get_daily_rates, get_dynamic_rates
from db.models import Currency
from services.chart.caption import ChartSeriesSummary, format_chart_caption
from services.chart.period import metric_period, period_label, period_window
from services.chart.render import ChartPanel, render_chart_png
from services.chart.series import analyze_series


@dataclass(frozen=True, slots=True)
class ChartResult:
    png: bytes
    caption: str
    weeks: int


async def build_chart(
    currencies: list[Currency],
    weeks: int,
) -> ChartResult | None:
    """Build chart image+caption for user currencies. None if nothing to draw."""
    try:
        prepared = await _prepare(currencies, weeks)
    except Exception:
        chart_errors_total.labels(reason="cbr").inc()
        raise

    if prepared is None:
        chart_errors_total.labels(reason="no_data").inc()
        return None

    panels, summaries, missing, date_from, date_to, label = prepared
    try:
        render_started = time.perf_counter()
        png = render_chart_png(
            panels, period_label=label, date_from=date_from, date_to=date_to
        )
        chart_render_duration_seconds.observe(time.perf_counter() - render_started)
    except Exception:
        chart_errors_total.labels(reason="render").inc()
        raise

    chart_builds_total.labels(period=metric_period(weeks)).inc()
    caption = format_chart_caption(
        period_label=label,
        date_from=date_from,
        date_to=date_to,
        series=summaries,
        missing=missing,
    )
    return ChartResult(png=png, caption=caption, weeks=weeks)


async def _prepare(currencies: list[Currency], weeks: int):
    date_from, date_to = period_window(weeks)
    daily = await get_daily_rates()

    panels: list[ChartPanel] = []
    summaries: list[ChartSeriesSummary] = []
    missing: list[str] = []

    async def fetch_one(currency: Currency):
        rate = daily.rates.get(currency.code)
        if rate is None or not rate.cbr_id:
            return currency.code, None
        points = await get_dynamic_rates(rate.cbr_id, date_from, date_to)
        extremes = analyze_series(points)
        if extremes is None:
            return currency.code, None
        return currency.code, (currency, points, extremes)

    results = await asyncio.gather(*(fetch_one(c) for c in currencies))
    for code, payload in results:
        if payload is None:
            missing.append(code)
            continue
        currency, points, extremes = payload
        panels.append(
            ChartPanel(
                code=currency.code,
                name=currency.name,
                points=points,
                extremes=extremes,
            )
        )
        summaries.append(
            ChartSeriesSummary(
                code=currency.code, name=currency.name, extremes=extremes
            )
        )

    if missing:
        chart_series_missing_total.inc(len(missing))

    if not panels:
        return None

    label = period_label(weeks)
    return panels, summaries, missing, date_from, date_to, label
