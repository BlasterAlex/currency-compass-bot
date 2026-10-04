from datetime import datetime, timedelta, timezone

from clients.cbr import CbrDailyRates, CbrRate
from db.models import Currency
from services.flags import currency_flag

# Moscow has no DST since 2014.
_MSK = timezone(timedelta(hours=3))

_DISCLAIMER = (
    "<i>Официальный курс Банка России - ориентир, не цена покупки или продажи в банке.</i>"
)


def _today_msk() -> str:
    return datetime.now(_MSK).strftime("%d.%m.%Y")


def format_rate_line(rate: CbrRate) -> str:
    value_str = f"{rate.value:f}".rstrip("0").rstrip(".")
    flag = currency_flag(rate.code)
    prefix = f"{flag} " if flag else ""
    line = f"{prefix}<b>{rate.code}</b> - {rate.name}\n{value_str} ₽ за {rate.nominal}"
    if rate.nominal != 1:
        per_unit = rate.value / rate.nominal
        per_unit_str = f"{per_unit:.6f}".rstrip("0").rstrip(".")
        line += f"\n{per_unit_str} ₽ за 1"
    return line


def format_rates_message(
    daily: CbrDailyRates,
    currencies: list[Currency],
) -> str:
    if not currencies:
        return (
            "Список валют пуст.\n"
            "Добавьте валюты через /currencies."
        )

    lines = [f"Курсы Банка России на <b>{_today_msk()}</b>:\n"]
    missing: list[str] = []

    for currency in currencies:
        rate = daily.rates.get(currency.code)
        if rate is None:
            missing.append(currency.code)
            continue
        lines.append(format_rate_line(rate))
        lines.append("")

    if missing:
        lines.append("Не найдены в фиде ЦБ: " + ", ".join(missing))
        lines.append("")

    lines.append(_DISCLAIMER)
    return "\n".join(lines).rstrip()
