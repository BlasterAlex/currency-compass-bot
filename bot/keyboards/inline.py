from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from clients.cbr import CbrRate
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
