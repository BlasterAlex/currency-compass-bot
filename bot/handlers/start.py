from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.metrics import track_command
from services.user import get_or_create_user

router = Router()

_WELCOME = (
    "Currency Compass - помощник для выбора момента покупки валюты за рубли.\n\n"
    "Сейчас доступны официальные курсы ЦБ по выбранным валютам.\n"
    "Операции покупки бот не выполняет.\n\n"
    "Команды в меню рядом с полем ввода:\n"
    "/currencies - управление списком валют\n"
    "/rate - текущие курсы ЦБ\n"
    "/chart - график курсов за период"
)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    with track_command("start"):
        await state.clear()
        await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await session.commit()
        await message.answer(_WELCOME, reply_markup=ReplyKeyboardRemove())
