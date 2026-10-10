from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from clients.cbr import CbrRate
from services.chart.period import quick_button
from services.flags import currency_label


def _choice_button(
    builder: InlineKeyboardBuilder,
    label: str,
    callback_data: str,
    *,
    selected: bool,
) -> None:
    builder.button(
        text=f"✓ {label}" if selected else label,
        callback_data="noop" if selected else callback_data,
    )


def currencies_keyboard(currencies: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for currency in currencies:
        builder.button(
            text=f"✕ {currency_label(currency.code, currency.name)}",
            callback_data=f"currency_remove:{currency.id}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="➕ Добавить валюту", callback_data="currencies:add"))
    return builder.as_markup()


def currency_search_keyboard(
    matches: list[CbrRate], tracked_codes: set[str]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rate in matches:
        label = currency_label(rate.code, rate.name)
        _choice_button(
            builder,
            label,
            f"currency_add:{rate.code}",
            selected=rate.code in tracked_codes,
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel"))
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="cancel")
    return builder.as_markup()


def empty_currencies_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить валюту", callback_data="currencies:add")
    builder.adjust(1)
    return builder.as_markup()


def period_keyboard(weeks: int) -> InlineKeyboardMarkup:
    marked = quick_button(weeks)
    builder = InlineKeyboardBuilder()
    for key, label, span in (
        ("week", "Неделя", 1),
        ("month", "Месяц", 4),
        ("half_year", "Полгода", 24),
    ):
        selected = marked == key
        builder.button(
            text=f"✓ {label}" if selected else label,
            callback_data="noop" if selected else f"chart:span:{span}",
        )
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(
            text="Другой",
            callback_data=f"chart:other:{weeks}",
        )
    )
    return builder.as_markup()


def unit_keyboard(weeks: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for unit, label in (("week", "Недели"), ("month", "Месяцы"), ("year", "Годы")):
        builder.button(text=label, callback_data=f"chart:unit:{unit}:{weeks}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="← Назад", callback_data=f"chart:menu:{weeks}"))
    return builder.as_markup()


def number_keyboard(unit: str, weeks: int) -> InlineKeyboardMarkup:
    step = {"week": 1, "month": 4, "year": 48}[unit]
    limit = {"week": 8, "month": 12, "year": 5}[unit]
    builder = InlineKeyboardBuilder()
    for count in range(1, limit + 1):
        selected = count * step == weeks
        builder.button(
            text=f"✓ {count}" if selected else str(count),
            callback_data=f"chart:menu:{weeks}" if selected else f"chart:pick:{unit}:{count}",
        )
    builder.adjust(5 if unit == "year" else 4)
    builder.row(InlineKeyboardButton(text="← Назад", callback_data=f"chart:other:{weeks}"))
    return builder.as_markup()
