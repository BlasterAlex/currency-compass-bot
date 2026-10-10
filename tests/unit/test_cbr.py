from datetime import date
from decimal import Decimal

from clients.cbr import (
    CbrSeriesPoint,
    clear_dynamic_cache,
    filter_currencies,
    get_dynamic_rates,
    normalize_series,
    parse_cbr_daily_xml,
    parse_cbr_dynamic_xml,
)

SAMPLE_XML = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="04.10.2026" name="Foreign Currency Market">
    <Valute ID="R01235">
        <NumCode>840</NumCode>
        <CharCode>USD</CharCode>
        <Nominal>1</Nominal>
        <Name>Доллар США</Name>
        <Value>92,1234</Value>
        <VunitRate>92,1234</VunitRate>
    </Valute>
    <Valute ID="R01239">
        <NumCode>978</NumCode>
        <CharCode>EUR</CharCode>
        <Nominal>1</Nominal>
        <Name>Евро</Name>
        <Value>100,5000</Value>
        <VunitRate>100,5000</VunitRate>
    </Valute>
    <Valute ID="R01717">
        <NumCode>860</NumCode>
        <CharCode>UZS</CharCode>
        <Nominal>10000</Nominal>
        <Name>Узбекских сумов</Name>
        <Value>70,4946</Value>
        <VunitRate>0,00704946</VunitRate>
    </Valute>
</ValCurs>
"""


def test_parse_cbr_daily_xml():
    daily = parse_cbr_daily_xml(SAMPLE_XML)
    assert daily.date == "04.10.2026"
    assert set(daily.rates) == {"USD", "EUR", "UZS"}

    usd = daily.rates["USD"]
    assert usd.name == "Доллар США"
    assert usd.nominal == 1
    assert usd.value == Decimal("92.1234")
    assert usd.cbr_id == "R01235"

    uzs = daily.rates["UZS"]
    assert uzs.nominal == 10000
    assert uzs.value == Decimal("70.4946")
    assert uzs.cbr_id == "R01717"


def test_filter_by_code():
    daily = parse_cbr_daily_xml(SAMPLE_XML)
    matches = filter_currencies(daily.rates, "usd")
    assert [m.code for m in matches] == ["USD"]


def test_filter_by_russian_name():
    daily = parse_cbr_daily_xml(SAMPLE_XML)
    matches = filter_currencies(daily.rates, "доллар")
    assert [m.code for m in matches] == ["USD"]


def test_filter_by_partial_name():
    daily = parse_cbr_daily_xml(SAMPLE_XML)
    matches = filter_currencies(daily.rates, "сум")
    assert [m.code for m in matches] == ["UZS"]


def test_filter_empty_query():
    daily = parse_cbr_daily_xml(SAMPLE_XML)
    assert filter_currencies(daily.rates, "   ") == []


SAMPLE_DYNAMIC = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01235" DateRange1="01.10.2026" DateRange2="09.10.2026" name="Foreign Currency Market Dynamic">
    <Record Date="02.10.2026" Id="R01235">
        <Nominal>1</Nominal>
        <Value>83,2454</Value>
        <VunitRate>83,2454</VunitRate>
    </Record>
    <Record Date="01.10.2026" Id="R01235">
        <Nominal>1</Nominal>
        <Value>83,5588</Value>
        <VunitRate>83,5588</VunitRate>
    </Record>
</ValCurs>
"""

SAMPLE_DYNAMIC_NO_VUNIT = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01717" DateRange1="01.10.2026" DateRange2="02.10.2026" name="Foreign Currency Market Dynamic">
    <Record Date="01.10.2026" Id="R01717">
        <Nominal>10000</Nominal>
        <Value>70,4946</Value>
    </Record>
</ValCurs>
"""


def test_parse_cbr_dynamic_xml_sorted():
    points = parse_cbr_dynamic_xml(SAMPLE_DYNAMIC)
    assert [p.date.isoformat() for p in points] == ["2026-10-01", "2026-10-02"]
    assert points[0].unit_rate == Decimal("83.5588")
    assert points[1].value == Decimal("83.2454")


def test_parse_cbr_dynamic_xml_unit_from_nominal():
    points = parse_cbr_dynamic_xml(SAMPLE_DYNAMIC_NO_VUNIT)
    assert len(points) == 1
    assert points[0].nominal == 10000
    assert points[0].unit_rate == Decimal("70.4946") / Decimal(10000)


def test_normalize_same_nominal_is_unchanged():
    points = [
        CbrSeriesPoint(date(2026, 10, 1), 1, Decimal("80"), Decimal("80")),
        CbrSeriesPoint(date(2026, 10, 2), 1, Decimal("90"), Decimal("90")),
    ]
    assert normalize_series(points) is points


def test_normalize_restates_uzs_blip_in_last_nominal():
    points = [
        CbrSeriesPoint(date(2022, 3, 6), 10000, Decimal("96.9828"), Decimal("0.00969828")),
        CbrSeriesPoint(date(2022, 3, 10), 1000, Decimal("10.6526"), Decimal("0.0106526")),
        CbrSeriesPoint(date(2022, 3, 17), 10000, Decimal("98.5216"), Decimal("0.00985216")),
    ]
    out = normalize_series(points)
    assert [point.nominal for point in out] == [10000, 10000, 10000]
    assert out[1].value == Decimal("106.526")


SAMPLE_DYNAMIC_NOMINAL_CHANGE = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01717" DateRange1="06.03.2022" DateRange2="17.03.2022" name="Foreign Currency Market Dynamic">
    <Record Date="06.03.2022" Id="R01717">
        <Nominal>10000</Nominal>
        <Value>96,9828</Value>
        <VunitRate>0,00969828</VunitRate>
    </Record>
    <Record Date="10.03.2022" Id="R01717">
        <Nominal>1000</Nominal>
        <Value>10,6526</Value>
        <VunitRate>0,0106526</VunitRate>
    </Record>
    <Record Date="17.03.2022" Id="R01717">
        <Nominal>10000</Nominal>
        <Value>98,5216</Value>
        <VunitRate>0,00985216</VunitRate>
    </Record>
</ValCurs>
"""


async def test_dynamic_cache_stores_normalized_series(monkeypatch):
    calls = 0

    async def fake_fetch(endpoint, url, params=None):
        nonlocal calls
        calls += 1
        return SAMPLE_DYNAMIC_NOMINAL_CHANGE

    monkeypatch.setattr("clients.cbr._fetch_cbr_text", fake_fetch)
    clear_dynamic_cache()
    start, end = date(2022, 3, 6), date(2022, 3, 17)
    points = await get_dynamic_rates("R01717", start, end)
    assert calls == 1
    assert points[1].nominal == 10000
    assert points[1].value == Decimal("106.526")

    again = await get_dynamic_rates("R01717", start, end)
    assert calls == 1
    assert again[1].value == Decimal("106.526")
    clear_dynamic_cache()
