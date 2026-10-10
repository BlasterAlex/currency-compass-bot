from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from clients.cbr import CbrSeriesPoint
from services.chart.series import SeriesExtremes
from services.flags import currency_flag
from services.rates import DISCLAIMER, format_nominal

_CAPTION_LIMIT = 1024


@dataclass(frozen=True, slots=True)
class ChartSeriesSummary:
    code: str
    name: str
    extremes: SeriesExtremes


def format_price(point: CbrSeriesPoint) -> str:
    return f"<b>{point.value:.2f}</b> ₽"


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _head(summary: ChartSeriesSummary, *, with_flag: bool) -> str:
    ex = summary.extremes
    nominal = f"за {format_nominal(ex.last.nominal)}"
    flag = currency_flag(summary.code) if with_flag else ""
    prefix = f"{flag} " if flag else ""
    return f"{prefix}{summary.code} ({nominal})"


def _full_currency_line(summary: ChartSeriesSummary) -> str:
    ex = summary.extremes
    head = _head(summary, with_flag=True)
    if ex.flat:
        return (
            f"{head} - курс за период не менялся: "
            f"{format_price(ex.last)} ({_fmt_date(ex.last.date)})"
        )
    return (
        f"{head} - "
        f"посл. {format_price(ex.last)} ({_fmt_date(ex.last.date)}), "
        f"мин. {format_price(ex.trough)} ({_fmt_date(ex.trough.date)}), "
        f"макс. {format_price(ex.peak)} ({_fmt_date(ex.peak.date)})"
    )


def _short_currency_line(summary: ChartSeriesSummary) -> str:
    ex = summary.extremes
    head = _head(summary, with_flag=False)
    if ex.flat:
        return f"{head} - {format_price(ex.last)} ({_fmt_date(ex.last.date)})"
    return (
        f"{head} - посл. {format_price(ex.last)}, "
        f"мин. {format_price(ex.trough)}, "
        f"макс. {format_price(ex.peak)}"
    )


def format_chart_caption(
    *,
    period_label: str,
    date_from: date,
    date_to: date,
    series: list[ChartSeriesSummary],
    missing: list[str],
) -> str:
    header = (
        f"Курсы ЦБ: {period_label} "
        f"(<b>{_fmt_date(date_from)} - {_fmt_date(date_to)}</b>)"
    )

    def build(currency_lines: list[str]) -> str:
        parts = [header, ""]
        parts.extend(currency_lines)
        if missing:
            if currency_lines:
                parts.append("")
            parts.append("Не найдены в фиде ЦБ: " + ", ".join(missing))
        parts.append("")
        parts.append(DISCLAIMER)
        return "\n".join(parts).rstrip()

    full = build([_full_currency_line(s) for s in series])
    if len(full) <= _CAPTION_LIMIT:
        return full

    short = build([_short_currency_line(s) for s in series])
    if len(short) <= _CAPTION_LIMIT:
        return short

    # Drop middle currencies until it fits; keep header + disclaimer.
    kept = list(series)
    while kept:
        kept.pop(len(kept) // 2)
        candidate = build([_short_currency_line(s) for s in kept])
        if len(candidate) <= _CAPTION_LIMIT:
            return candidate

    return build([])
