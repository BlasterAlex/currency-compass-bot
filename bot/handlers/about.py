from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.metrics import track_command

router = Router()

ISSUES_URL = "https://github.com/BlasterAlex/currency-compass-bot/issues"

_ABOUT = (
    "<b>О боте</b>\n\n"
    "Currency Compass показывает официальные курсы валют ЦБ. "
    "Покупку валюты бот не выполняет.\n\n"
    f'Ошибки и идеи — на странице <a href="{ISSUES_URL}">Issues</a>.'
)

_ABOUT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Открыть Issues", url=ISSUES_URL)]]
)


@router.message(Command("about"))
async def cmd_about(message: Message, state: FSMContext) -> None:
    with track_command("about"):
        await state.clear()
        await message.answer(_ABOUT, reply_markup=_ABOUT_KEYBOARD)
