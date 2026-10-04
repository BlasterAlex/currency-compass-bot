import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    cancel_keyboard,
    currencies_keyboard,
    currency_search_keyboard,
    empty_currencies_keyboard,
)
from bot.states.currency import CurrencyForm
from clients.cbr import get_daily_rates
from services.currency import (
    add_user_currency,
    get_or_create_currency,
    get_user_currencies,
    remove_user_currency,
    search_cbr_currencies,
)
from services.flags import currency_label
from services.user import get_or_create_user

logger = logging.getLogger(__name__)

router = Router()


def _currencies_view(currencies: list) -> tuple[str, object]:
    if not currencies:
        return (
            "Список валют пуст.\nНажмите «Добавить валюту» и введите код или название.",
            empty_currencies_keyboard(),
        )
    text = "Ваши валюты:\n" + "\n".join(f"• {currency_label(c.code, c.name)}" for c in currencies)
    return text, currencies_keyboard(currencies)


@router.message(Command("currencies"))
async def cmd_currencies(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await session.commit()
    currencies = await get_user_currencies(session, user.id)
    text, markup = _currencies_view(currencies)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "currencies:add")
async def on_currencies_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CurrencyForm.waiting_for_search)
    await callback.message.answer(
        "Введите код или название валюты (например: USD или доллар):",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(CurrencyForm.waiting_for_search, ~F.text.startswith("/"))
async def on_currency_search(message: Message, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    if not query:
        return

    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await session.commit()

    try:
        matches = await search_cbr_currencies(query)
    except Exception:
        logger.exception("CBR search failed query=%r", query)
        await message.answer(
            "Не удалось получить список валют ЦБ. Попробуйте позже.",
            reply_markup=cancel_keyboard(),
        )
        return

    if not matches:
        await message.answer(
            "Ничего не найдено. Попробуйте другой запрос.",
            reply_markup=cancel_keyboard(),
        )
        return

    tracked = {c.code for c in await get_user_currencies(session, user.id)}
    await message.answer(
        f"Найдено: {len(matches)}. Выберите валюту:",
        reply_markup=currency_search_keyboard(matches, tracked),
    )


@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await get_or_create_user(
        session, callback.from_user.id, callback.from_user.username
    )
    await session.commit()
    currencies = await get_user_currencies(session, user.id)
    text, markup = _currencies_view(currencies)
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("currency_add:"))
async def on_currency_add(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    code = callback.data.split(":", 1)[1]

    try:
        daily = await get_daily_rates()
    except Exception:
        logger.exception("CBR fetch failed on add code=%s", code)
        await callback.answer("Не удалось получить данные ЦБ.", show_alert=True)
        return

    rate = daily.rates.get(code)
    if rate is None:
        await callback.answer("Неизвестная валюта.", show_alert=True)
        return

    user = await get_or_create_user(
        session, callback.from_user.id, callback.from_user.username
    )
    await session.commit()

    currency = await get_or_create_currency(session, rate.code, rate.name)
    added = await add_user_currency(session, user, currency.id)
    await state.clear()

    if added:
        currencies = await get_user_currencies(session, user.id)
        label = currency_label(rate.code, rate.name)
        text = f"✓ {label} добавлена.\n\n" + _currencies_view(currencies)[0]
        await callback.message.answer(text, reply_markup=currencies_keyboard(currencies))
        await callback.answer()
    else:
        await callback.answer("Эта валюта уже в списке.", show_alert=True)


@router.callback_query(F.data.startswith("currency_remove:"))
async def on_currency_remove(callback: CallbackQuery, session: AsyncSession) -> None:
    currency_id = int(callback.data.split(":", 1)[1])

    user = await get_or_create_user(
        session, callback.from_user.id, callback.from_user.username
    )
    await session.commit()

    await remove_user_currency(session, user, currency_id)

    currencies = await get_user_currencies(session, user.id)
    text, markup = _currencies_view(currencies)
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()
