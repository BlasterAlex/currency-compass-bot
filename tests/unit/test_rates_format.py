from datetime import datetime, timedelta, timezone
from decimal import Decimal

from clients.cbr import CbrDailyRates, CbrRate
from db.models import Currency
from services.rates import format_rate_line, format_rates_message

_MSK = timezone(timedelta(hours=3))


def test_format_rate_line_nominal_one():
    rate = CbrRate(code="USD", name="Доллар США", nominal=1, value=Decimal("92.1234"))
    text = format_rate_line(rate)
    assert "🇺🇸" in text
    assert "USD" in text
    assert " - " in text
    assert "—" not in text
    assert "92.1234 ₽ за 1" in text
    assert text.count("₽ за 1") == 1


def test_format_rate_line_with_nominal():
    rate = CbrRate(code="UZS", name="Узбекских сумов", nominal=10000, value=Decimal("70.4946"))
    text = format_rate_line(rate)
    assert "70.4946 ₽ за 10000" in text
    assert "₽ за 1" in text


def test_format_rates_message_empty():
    daily = CbrDailyRates(date="03.10.2026", rates={})
    text = format_rates_message(daily, [])
    assert "пуст" in text.lower()


def test_format_rates_message_uses_today_not_cbr_date():
    daily = CbrDailyRates(
        date="03.10.2026",
        rates={
            "USD": CbrRate(code="USD", name="Доллар США", nominal=1, value=Decimal("92.12")),
        },
    )
    currencies = [Currency(id=1, code="USD", name="Доллар США")]
    text = format_rates_message(daily, currencies)
    today = datetime.now(_MSK).strftime("%d.%m.%Y")
    assert f"на <b>{today}</b>:" in text
    assert "на 03.10.2026:" not in text
    assert "<i>" in text and "</i>" in text
    assert "не цена" in text
