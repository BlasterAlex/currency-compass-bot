import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.currency import (
    add_user_currency,
    get_or_create_currency,
    get_user_currencies,
    remove_user_currency,
)
from services.user import get_or_create_user


@pytest.mark.asyncio
async def test_get_or_create_currency_creates(session: AsyncSession):
    currency = await get_or_create_currency(session, "EUR", "Евро")
    assert currency.id is not None
    assert currency.code == "EUR"
    assert currency.name == "Евро"


@pytest.mark.asyncio
async def test_get_or_create_currency_idempotent(session: AsyncSession):
    c1 = await get_or_create_currency(session, "EUR", "Евро")
    c2 = await get_or_create_currency(session, "EUR", "Евро")
    assert c1.id == c2.id


@pytest.mark.asyncio
async def test_get_user_currencies_empty(session: AsyncSession, user):
    assert await get_user_currencies(session, user.id) == []


@pytest.mark.asyncio
async def test_add_user_currency(session: AsyncSession, user, currency):
    added = await add_user_currency(session, user, currency.id)
    assert added is True
    currencies = await get_user_currencies(session, user.id)
    assert len(currencies) == 1
    assert currencies[0].code == "USD"


@pytest.mark.asyncio
async def test_add_user_currency_duplicate(session: AsyncSession, user, currency):
    await add_user_currency(session, user, currency.id)
    added = await add_user_currency(session, user, currency.id)
    assert added is False


@pytest.mark.asyncio
async def test_remove_user_currency(session: AsyncSession, user, currency):
    await add_user_currency(session, user, currency.id)
    await remove_user_currency(session, user, currency.id)
    assert await get_user_currencies(session, user.id) == []


@pytest.mark.asyncio
async def test_get_or_create_user(session: AsyncSession):
    u1 = await get_or_create_user(session, 999888777, "newuser")
    u2 = await get_or_create_user(session, 999888777, "newuser")
    assert u1.id == u2.id
    assert u1.telegram_id == 999888777
