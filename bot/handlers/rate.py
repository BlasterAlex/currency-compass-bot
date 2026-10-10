import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.metrics import track_command
from clients.cbr import get_daily_rates
from services.currency import get_user_currencies
from services.rates import format_rates_message
from services.user import get_or_create_user

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("rate"))
async def cmd_rate(message: Message, session: AsyncSession, state: FSMContext) -> None:
    with track_command("rate") as track:
        await state.clear()
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await session.commit()

        currencies = await get_user_currencies(session, user.id)
        if not currencies:
            track.result = "empty"
            await message.answer("Список валют пуст.\nДобавьте валюты через /currencies.")
            return

        try:
            daily = await get_daily_rates()
        except Exception:
            track.result = "cbr_error"
            logger.exception("CBR fetch failed for rates telegram_id=%d", message.from_user.id)
            await message.answer("Не удалось получить курсы ЦБ. Попробуйте позже.")
            return

        text = format_rates_message(daily, currencies)
        await message.answer(text)
