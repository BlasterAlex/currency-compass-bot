from decimal import Decimal

from clients.cbr import filter_currencies, parse_cbr_daily_xml

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

    uzs = daily.rates["UZS"]
    assert uzs.nominal == 10000
    assert uzs.value == Decimal("70.4946")


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
