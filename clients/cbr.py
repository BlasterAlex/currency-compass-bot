"""Bank of Russia daily exchange rates client."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import aiohttp

logger = logging.getLogger(__name__)

_DAILY_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
_CACHE_TTL = 3600  # 1 hour


@dataclass(frozen=True, slots=True)
class CbrRate:
    code: str
    name: str
    nominal: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class CbrDailyRates:
    date: str
    rates: dict[str, CbrRate]


_cache: CbrDailyRates | None = None
_cache_at: float = 0.0


def parse_cbr_daily_xml(xml_text: str) -> CbrDailyRates:
    """Parse XML_daily.asp payload into structured rates."""
    root = ET.fromstring(xml_text)
    date = root.attrib.get("Date", "")
    rates: dict[str, CbrRate] = {}

    for valute in root.findall("Valute"):
        code = (valute.findtext("CharCode") or "").strip()
        name = (valute.findtext("Name") or "").strip()
        nominal_raw = (valute.findtext("Nominal") or "").strip()
        value_raw = (valute.findtext("Value") or "").strip().replace(",", ".")
        if not code or not name or not nominal_raw or not value_raw:
            continue
        try:
            nominal = int(nominal_raw)
            value = Decimal(value_raw)
        except (ValueError, InvalidOperation):
            logger.warning("skip malformed valute code=%s", code)
            continue
        rates[code] = CbrRate(code=code, name=name, nominal=nominal, value=value)

    return CbrDailyRates(date=date, rates=rates)


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


async def get_daily_rates(*, force_refresh: bool = False) -> CbrDailyRates:
    """Return daily CBR rates, cached in memory for _CACHE_TTL seconds."""
    global _cache, _cache_at

    if (
        not force_refresh
        and _cache is not None
        and time.monotonic() - _cache_at < _CACHE_TTL
    ):
        return _cache

    async with aiohttp.ClientSession() as http:
        async with http.get(_DAILY_URL) as resp:
            resp.raise_for_status()
            # CBR serves Windows-1251; aiohttp may not decode it correctly via charset.
            raw = await resp.read()
            encoding = resp.charset or "windows-1251"
            try:
                text = raw.decode(encoding)
            except LookupError:
                text = raw.decode("windows-1251")

    daily = parse_cbr_daily_xml(text)
    _cache = daily
    _cache_at = time.monotonic()
    logger.info("fetched CBR daily rates date=%s count=%d", daily.date, len(daily.rates))
    return daily
