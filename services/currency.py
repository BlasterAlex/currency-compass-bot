import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clients.cbr import CbrRate, filter_currencies, get_daily_rates
from db.models import Currency, User, UserCurrency

logger = logging.getLogger(__name__)

_MAX_SEARCH_RESULTS = 20


async def get_or_create_currency(session: AsyncSession, code: str, name: str) -> Currency:
    result = await session.execute(select(Currency).where(Currency.code == code))
    currency = result.scalar_one_or_none()
    if currency is None:
        currency = Currency(code=code, name=name)
        session.add(currency)
        await session.flush()
    elif currency.name != name:
        currency.name = name
        await session.flush()
    return currency


async def get_user_currencies(session: AsyncSession, user_id: int) -> list[Currency]:
    result = await session.execute(
        select(Currency)
        .join(UserCurrency, UserCurrency.currency_id == Currency.id)
        .where(UserCurrency.user_id == user_id)
        .order_by(Currency.code)
    )
    return list(result.scalars().all())


async def add_user_currency(session: AsyncSession, user: User, currency_id: int) -> bool:
    exists = await session.execute(
        select(UserCurrency).where(
            UserCurrency.user_id == user.id,
            UserCurrency.currency_id == currency_id,
        )
    )
    if exists.scalar_one_or_none() is not None:
        return False
    session.add(UserCurrency(user_id=user.id, currency_id=currency_id))
    await session.commit()
    logger.info("added currency telegram_id=%d currency_id=%d", user.telegram_id, currency_id)
    return True


async def remove_user_currency(session: AsyncSession, user: User, currency_id: int) -> None:
    result = await session.execute(
        select(UserCurrency).where(
            UserCurrency.user_id == user.id,
            UserCurrency.currency_id == currency_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()
        logger.info(
            "removed currency telegram_id=%d currency_id=%d",
            user.telegram_id,
            currency_id,
        )


async def search_cbr_currencies(query: str) -> list[CbrRate]:
    daily = await get_daily_rates()
    matches = filter_currencies(daily.rates, query)
    return matches[:_MAX_SEARCH_RESULTS]
