from datetime import datetime, timedelta, timezone

from clients.cbr import CbrDailyRates, CbrRate
from db.models import Currency
from services.flags import currency_flag

# Moscow has no DST since 2014.
_MSK = timezone(timedelta(hours=3))

DISCLAIMER = (
    "<i>Официальный курс ЦБ - ориентир, не цена покупки или продажи в банке.</i>"
)


def _today_msk() -> str:
    return datetime.now(_MSK).strftime("%d.%m.%Y")


def format_nominal(nominal: int) -> str:
    if nominal >= 1000 and nominal % 1000 == 0:
        return f"{nominal // 1000}K"
    return str(nominal)


def format_rate_line(rate: CbrRate) -> str:
    value_str = f"{rate.value:.2f}"
    flag = currency_flag(rate.code)
    prefix = f"{flag} " if flag else ""
    return (
        f"{prefix}<b>{rate.code}</b> - {rate.name}\n"
        f"{value_str} ₽ за {format_nominal(rate.nominal)}"
    )


def format_rates_message(
    daily: CbrDailyRates,
    currencies: list[Currency],
) -> str:
    if not currencies:
        return (
            "Список валют пуст.\n"
            "Добавьте валюты через /currencies."
        )

    lines = [f"Курсы ЦБ на <b>{_today_msk()}</b>:\n"]
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

    lines.append(DISCLAIMER)
    shown = len(currencies) - len(missing)
    if shown > 0:
        lines.append("")
        lines.append("График за период: /chart")
    return "\n".join(lines).rstrip()
