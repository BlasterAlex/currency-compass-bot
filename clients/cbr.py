"""Bank of Russia daily exchange rates client."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import aiohttp

from bot.metrics import record_cbr_fetch

logger = logging.getLogger(__name__)

_DAILY_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
_DYNAMIC_URL = "https://www.cbr.ru/scripts/XML_dynamic.asp"
_CACHE_TTL = 3600  # 1 hour


@dataclass(frozen=True, slots=True)
class CbrRate:
    code: str
    name: str
    nominal: int
    value: Decimal
    cbr_id: str


@dataclass(frozen=True, slots=True)
class CbrDailyRates:
    date: str
    rates: dict[str, CbrRate]


@dataclass(frozen=True, slots=True)
class CbrSeriesPoint:
    date: date
    nominal: int
    value: Decimal
    unit_rate: Decimal


_cache: CbrDailyRates | None = None
_cache_at: float = 0.0

_dynamic_cache: dict[tuple[str, str, str], tuple[float, list[CbrSeriesPoint]]] = {}


def _decode_cbr_body(raw: bytes, charset: str | None) -> str:
    encoding = charset or "windows-1251"
    try:
        return raw.decode(encoding)
    except LookupError:
        return raw.decode("windows-1251")


def parse_cbr_daily_xml(xml_text: str) -> CbrDailyRates:
    """Parse XML_daily.asp payload into structured rates."""
    root = ET.fromstring(xml_text)
    date_str = root.attrib.get("Date", "")
    rates: dict[str, CbrRate] = {}

    for valute in root.findall("Valute"):
        code = (valute.findtext("CharCode") or "").strip()
        name = (valute.findtext("Name") or "").strip()
        nominal_raw = (valute.findtext("Nominal") or "").strip()
        value_raw = (valute.findtext("Value") or "").strip().replace(",", ".")
        cbr_id = (valute.attrib.get("ID") or "").strip()
        if not code or not name or not nominal_raw or not value_raw:
            continue
        try:
            nominal = int(nominal_raw)
            value = Decimal(value_raw)
        except (ValueError, InvalidOperation):
            logger.warning("skip malformed valute code=%s", code)
            continue
        rates[code] = CbrRate(
            code=code, name=name, nominal=nominal, value=value, cbr_id=cbr_id
        )

    return CbrDailyRates(date=date_str, rates=rates)


def parse_cbr_dynamic_xml(xml_text: str) -> list[CbrSeriesPoint]:
    """Parse XML_dynamic.asp payload into dated points sorted ascending."""
    root = ET.fromstring(xml_text)
    points: list[CbrSeriesPoint] = []

    for record in root.findall("Record"):
        date_raw = (record.attrib.get("Date") or "").strip()
        nominal_raw = (record.findtext("Nominal") or "").strip()
        value_raw = (record.findtext("Value") or "").strip().replace(",", ".")
        unit_raw = (record.findtext("VunitRate") or "").strip().replace(",", ".")
        if not date_raw or not nominal_raw or not value_raw:
            continue
        try:
            point_date = datetime.strptime(date_raw, "%d.%m.%Y").date()
            nominal = int(nominal_raw)
            value = Decimal(value_raw)
            if unit_raw:
                unit_rate = Decimal(unit_raw)
            else:
                unit_rate = value / Decimal(nominal)
        except (ValueError, InvalidOperation, ZeroDivisionError):
            logger.warning("skip malformed dynamic record date=%s", date_raw)
            continue
        points.append(
            CbrSeriesPoint(
                date=point_date, nominal=nominal, value=value, unit_rate=unit_rate
            )
        )

    points.sort(key=lambda p: p.date)
    return points


def normalize_series(points: list[CbrSeriesPoint]) -> list[CbrSeriesPoint]:
    """Restate every quote in the last point's nominal.

    CBR sometimes changes Nominal inside a window. Raw Value is then a
    different bundle size, so the line and the title («за 10K») disagree.
    """
    if not points or all(point.nominal == points[-1].nominal for point in points):
        return points
    nominal = points[-1].nominal
    scale = Decimal(nominal)
    return [
        CbrSeriesPoint(
            date=point.date,
            nominal=nominal,
            value=point.unit_rate * scale,
            unit_rate=point.unit_rate,
        )
        for point in points
    ]


def filter_currencies(rates: dict[str, CbrRate], query: str) -> list[CbrRate]:
    """Filter currencies by ISO code or Russian name substring."""
    needle = query.strip().lower()
    if not needle:
        return []
    return [
        rate
        for rate in rates.values()
        if needle in rate.code.lower() or needle in rate.name.lower()
    ]


def clear_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = 0.0


def clear_dynamic_cache() -> None:
    _dynamic_cache.clear()


async def _fetch_cbr_text(endpoint: str, url: str, params: dict[str, str] | None = None) -> str:
    started = time.perf_counter()
    result = "error"
    try:
        async with aiohttp.ClientSession() as http:
            async with http.get(url, params=params) as resp:
                if resp.status >= 400:
                    result = "http"
                resp.raise_for_status()
                raw = await resp.read()
                text = _decode_cbr_body(raw, resp.charset)
                result = "ok"
                return text
    finally:
        record_cbr_fetch(endpoint, result, time.perf_counter() - started)


async def get_daily_rates(*, force_refresh: bool = False) -> CbrDailyRates:
    """Return daily CBR rates, cached in memory for _CACHE_TTL seconds."""
    global _cache, _cache_at

    if (
        not force_refresh
        and _cache is not None
        and time.monotonic() - _cache_at < _CACHE_TTL
    ):
        return _cache

    text = await _fetch_cbr_text("daily", _DAILY_URL)
    daily = parse_cbr_daily_xml(text)
    _cache = daily
    _cache_at = time.monotonic()
    logger.info("fetched CBR daily rates date=%s count=%d", daily.date, len(daily.rates))
    return daily


async def get_dynamic_rates(
    cbr_id: str,
    date_from: date,
    date_to: date,
    *,
    force_refresh: bool = False,
) -> list[CbrSeriesPoint]:
    """Return dynamic CBR series for one currency, cached for _CACHE_TTL seconds."""
    key = (cbr_id, date_from.isoformat(), date_to.isoformat())
    if not force_refresh:
        cached = _dynamic_cache.get(key)
        if cached is not None and time.monotonic() - cached[0] < _CACHE_TTL:
            return cached[1]

    params = {
        "date_req1": date_from.strftime("%d/%m/%Y"),
        "date_req2": date_to.strftime("%d/%m/%Y"),
        "VAL_NM_RQ": cbr_id,
    }
    text = await _fetch_cbr_text("dynamic", _DYNAMIC_URL, params)
    points = normalize_series(parse_cbr_dynamic_xml(text))
    _dynamic_cache[key] = (time.monotonic(), points)
    logger.info(
        "fetched CBR dynamic rates cbr_id=%s from=%s to=%s count=%d",
        cbr_id,
        date_from.isoformat(),
        date_to.isoformat(),
        len(points),
    )
    return points
