import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import number_keyboard, period_keyboard, unit_keyboard
from bot.metrics import chart_edit_failures_total, chart_errors_total, track_command
from services.chart import build_chart
from services.chart.period import LEGACY_WEEKS, is_allowed_weeks, weeks_for_pick
from services.currency import get_user_currencies
from services.user import get_or_create_user

logger = logging.getLogger(__name__)

router = Router()

_CBR_ERROR = "Не удалось получить курсы ЦБ. Попробуйте позже."
_EMPTY = "Список валют пуст.\nДобавьте валюты через /currencies."
_NO_DATA = "Нет данных ЦБ для выбранных валют за этот период."
_UNITS = ("week", "month", "year")


def _photo(png: bytes) -> BufferedInputFile:
    return BufferedInputFile(png, filename="chart.png")


def _parse_weeks(raw: str) -> int | None:
    try:
        weeks = int(raw)
    except ValueError:
        return None
    if not is_allowed_weeks(weeks):
        return None
    return weeks


async def _invalid(callback: CallbackQuery) -> None:
    chart_errors_total.labels(reason="invalid_span").inc()
    await callback.answer()


async def _show_markup(callback: CallbackQuery, markup) -> None:
    await callback.answer()
    if callback.message is None:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        logger.exception("chart keyboard edit failed")


async def _send_chart(message: Message, session: AsyncSession, weeks: int) -> None:
    with track_command("chart") as track:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await session.commit()

        currencies = await get_user_currencies(session, user.id)
        if not currencies:
            track.result = "empty"
            await message.answer(_EMPTY)
            return

        try:
            result = await build_chart(currencies, weeks)
        except Exception:
            track.result = "cbr_error"
            logger.exception("chart build failed telegram_id=%d", message.from_user.id)
            await message.answer(_CBR_ERROR)
            return

        if result is None:
            track.result = "no_data"
            await message.answer(_NO_DATA)
            return

        await message.answer_photo(
            _photo(result.png),
            caption=result.caption,
            reply_markup=period_keyboard(result.weeks),
        )


async def _rebuild(callback: CallbackQuery, session: AsyncSession, weeks: int) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return

    with track_command("chart") as track:
        user = await get_or_create_user(
            session, callback.from_user.id, callback.from_user.username
        )
        await session.commit()
        currencies = await get_user_currencies(session, user.id)
        if not currencies:
            track.result = "empty"
            await callback.message.answer(_EMPTY)
            return

        try:
            result = await build_chart(currencies, weeks)
        except Exception:
            track.result = "cbr_error"
            logger.exception("chart rebuild failed telegram_id=%d", callback.from_user.id)
            await callback.message.answer(_CBR_ERROR)
            return

        if result is None:
            track.result = "no_data"
            await callback.message.answer(_NO_DATA)
            return

        media = InputMediaPhoto(media=_photo(result.png), caption=result.caption)
        markup = period_keyboard(result.weeks)
        try:
            await callback.message.edit_media(media=media, reply_markup=markup)
        except Exception:
            chart_edit_failures_total.inc()
            logger.exception("chart edit_media failed; sending new photo")
            await callback.message.answer_photo(
                _photo(result.png),
                caption=result.caption,
                reply_markup=markup,
            )


@router.message(Command("chart"))
async def cmd_chart(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await _send_chart(message, session, 1)


@router.callback_query(F.data.startswith("chart:period:"))
async def on_chart_legacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    raw = (callback.data or "").removeprefix("chart:period:")
    weeks = LEGACY_WEEKS.get(raw)
    if weeks is None:
        await _invalid(callback)
        return
    await _rebuild(callback, session, weeks)


@router.callback_query(F.data.startswith("chart:span:"))
async def on_chart_span(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    weeks = _parse_weeks((callback.data or "").removeprefix("chart:span:"))
    if weeks is None:
        await _invalid(callback)
        return
    await _rebuild(callback, session, weeks)


@router.callback_query(F.data.startswith("chart:pick:"))
async def on_chart_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    rest = (callback.data or "").removeprefix("chart:pick:")
    unit, _, raw = rest.partition(":")
    try:
        count = int(raw)
    except ValueError:
        await _invalid(callback)
        return
    weeks = weeks_for_pick(unit, count)
    if weeks is None:
        await _invalid(callback)
        return
    await _rebuild(callback, session, weeks)


@router.callback_query(F.data.startswith("chart:other:"))
async def on_chart_other(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    weeks = _parse_weeks((callback.data or "").removeprefix("chart:other:"))
    if weeks is None:
        await _invalid(callback)
        return
    await _show_markup(callback, unit_keyboard(weeks))


@router.callback_query(F.data.startswith("chart:unit:"))
async def on_chart_unit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    rest = (callback.data or "").removeprefix("chart:unit:")
    unit, _, raw = rest.partition(":")
    if unit not in _UNITS:
        await _invalid(callback)
        return
    weeks = _parse_weeks(raw)
    if weeks is None:
        await _invalid(callback)
        return
    await _show_markup(callback, number_keyboard(unit, weeks))


@router.callback_query(F.data.startswith("chart:menu:"))
async def on_chart_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    weeks = _parse_weeks((callback.data or "").removeprefix("chart:menu:"))
    if weeks is None:
        await _invalid(callback)
        return
    await _show_markup(callback, period_keyboard(weeks))
