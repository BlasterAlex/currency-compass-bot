from datetime import datetime, timedelta, timezone
from decimal import Decimal

from clients.cbr import CbrDailyRates, CbrRate
from db.models import Currency
from services.rates import format_nominal, format_rate_line, format_rates_message

_MSK = timezone(timedelta(hours=3))


def test_format_nominal():
    assert format_nominal(1) == "1"
    assert format_nominal(10) == "10"
    assert format_nominal(100) == "100"
    assert format_nominal(1000) == "1K"
    assert format_nominal(10000) == "10K"


def test_format_rate_line_nominal_one():
    rate = CbrRate(
        code="USD", name="Доллар США", nominal=1, value=Decimal("92.1234"), cbr_id="R01235"
    )
    text = format_rate_line(rate)
    assert "🇺🇸" in text
    assert "USD" in text
    assert " - " in text
    assert "—" not in text
    assert "92.12 ₽ за 1" in text
    assert text.rstrip().endswith("за 1")


def test_format_rate_line_with_nominal():
    rate = CbrRate(
        code="UZS",
        name="Узбекских сумов",
        nominal=10000,
        value=Decimal("70.4946"),
        cbr_id="R01717",
    )
    text = format_rate_line(rate)
    assert "70.49 ₽ за 10K" in text
    assert text.rstrip().endswith("10K")
    assert "10000" not in text


def test_format_rates_message_empty():
    daily = CbrDailyRates(date="03.10.2026", rates={})
    text = format_rates_message(daily, [])
    assert "пуст" in text.lower()


def test_format_rates_message_uses_today_not_cbr_date():
    daily = CbrDailyRates(
        date="03.10.2026",
        rates={
            "USD": CbrRate(
                code="USD",
                name="Доллар США",
                nominal=1,
                value=Decimal("92.12"),
                cbr_id="R01235",
            ),
        },
    )
    currencies = [Currency(id=1, code="USD", name="Доллар США")]
    text = format_rates_message(daily, currencies)
    today = datetime.now(_MSK).strftime("%d.%m.%Y")
    assert f"на <b>{today}</b>:" in text
    assert "на 03.10.2026:" not in text
    assert "<i>" in text and "</i>" in text
    assert "не цена" in text
    assert "График за период: /chart" in text


def test_format_rates_message_empty_has_no_chart_hint():
    text = format_rates_message(CbrDailyRates(date="03.10.2026", rates={}), [])
    assert "/chart" not in text
