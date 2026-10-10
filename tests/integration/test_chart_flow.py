from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.chart import _send_chart, on_chart_legacy, on_chart_pick, on_chart_span
from bot.metrics import (
    bot_commands_total,
    chart_edit_failures_total,
    chart_errors_total,
)
from clients.cbr import clear_cache, clear_dynamic_cache
from services.currency import add_user_currency, get_or_create_currency
from services.user import get_or_create_user

_DAILY = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="10.10.2026" name="Foreign Currency Market">
    <Valute ID="R01235">
        <CharCode>USD</CharCode>
        <Nominal>1</Nominal>
        <Name>Доллар США</Name>
        <Value>84,9048</Value>
        <VunitRate>84,9048</VunitRate>
    </Valute>
    <Valute ID="R01717">
        <CharCode>UZS</CharCode>
        <Nominal>10000</Nominal>
        <Name>Узбекских сумов</Name>
        <Value>71,6704</Value>
        <VunitRate>0,00716704</VunitRate>
    </Valute>
</ValCurs>
"""

_DYNAMIC_USD = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01235" DateRange1="04.10.2026" DateRange2="10.10.2026">
    <Record Date="04.10.2026" Id="R01235">
        <Nominal>1</Nominal>
        <Value>80,0000</Value>
        <VunitRate>80,0000</VunitRate>
    </Record>
    <Record Date="10.10.2026" Id="R01235">
        <Nominal>1</Nominal>
        <Value>90,0000</Value>
        <VunitRate>90,0000</VunitRate>
    </Record>
</ValCurs>
"""

_DYNAMIC_UZS = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs ID="R01717" DateRange1="06.03.2022" DateRange2="17.03.2022">
    <Record Date="06.03.2022" Id="R01717">
        <Nominal>10000</Nominal>
        <Value>96,9828</Value>
        <VunitRate>0,00969828</VunitRate>
    </Record>
    <Record Date="10.03.2022" Id="R01717">
        <Nominal>1000</Nominal>
        <Value>10,6526</Value>
        <VunitRate>0,0106526</VunitRate>
    </Record>
    <Record Date="17.03.2022" Id="R01717">
        <Nominal>10000</Nominal>
        <Value>98,5216</Value>
        <VunitRate>0,00985216</VunitRate>
    </Record>
</ValCurs>
"""


def _metric(metric, **labels) -> float:
    return metric.labels(**labels)._value.get()


class _From:
    def __init__(self, user_id: int) -> None:
        self.id = user_id
        self.username = "tester"


class _Message:
    def __init__(self, user_id: int) -> None:
        self.from_user = _From(user_id)
        self.texts: list[str] = []
        self.photos: list[tuple[str | None, object]] = []
        self.edit_error: Exception | None = None

    async def answer(self, text: str, **kwargs) -> None:
        self.texts.append(text)

    async def answer_photo(self, photo, caption=None, reply_markup=None, **kwargs) -> None:
        self.photos.append((caption, reply_markup))

    async def edit_media(self, media=None, reply_markup=None, **kwargs) -> None:
        if self.edit_error is not None:
            raise self.edit_error
        self.photos.append((media.caption, reply_markup))


class _Callback:
    def __init__(self, data: str, message: _Message) -> None:
        self.data = data
        self.message = message
        self.from_user = message.from_user

    async def answer(self, *args, **kwargs) -> None:
        return None


def _texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


@pytest.fixture(autouse=True)
def _fresh_cbr_cache():
    clear_cache()
    clear_dynamic_cache()
    yield
    clear_cache()
    clear_dynamic_cache()


@pytest.fixture
def cbr(monkeypatch):
    async def fetch(endpoint, url, params=None):
        if endpoint == "daily":
            return _DAILY
        if (params or {}).get("VAL_NM_RQ") == "R01717":
            return _DYNAMIC_UZS
        return _DYNAMIC_USD

    monkeypatch.setattr("clients.cbr._fetch_cbr_text", fetch)


async def _track(session: AsyncSession, code: str, name: str, telegram_id: int) -> None:
    user = await get_or_create_user(session, telegram_id, "tester")
    currency = await get_or_create_currency(session, code, name)
    await add_user_currency(session, user, currency.id)
    await session.commit()


async def test_chart_empty_list(session: AsyncSession):
    message = _Message(501)
    before = _metric(bot_commands_total, command="chart", result="empty")
    await _send_chart(message, session, 1)
    assert message.photos == []
    assert "Список валют пуст" in message.texts[0]
    assert _metric(bot_commands_total, command="chart", result="empty") == before + 1


async def test_chart_week_uses_saved_currencies(session: AsyncSession, cbr):
    await _track(session, "USD", "Доллар США", 502)
    message = _Message(502)
    await _send_chart(message, session, 1)
    caption, markup = message.photos[0]
    assert "Курсы ЦБ: Неделя" in caption
    assert "USD (за 1)" in caption
    assert "<b>80.00</b>" in caption
    assert "<b>90.00</b>" in caption
    assert _texts(markup)[0] == "✓ Неделя"


async def test_custom_months_and_week_collapse(session: AsyncSession, cbr):
    await _track(session, "USD", "Доллар США", 503)
    message = _Message(503)
    state = AsyncMock()

    await on_chart_pick(_Callback("chart:pick:month:3", message), session, state)
    caption, markup = message.photos[-1]
    assert "Курсы ЦБ: 3 месяца" in caption
    assert "Другой" in _texts(markup)
    assert "✓ Другой" not in _texts(markup)
    assert "✓ Месяц" not in _texts(markup)

    await on_chart_pick(_Callback("chart:pick:week:4", message), session, state)
    caption, markup = message.photos[-1]
    assert "Курсы ЦБ: Месяц" in caption
    assert "4 недели" not in caption
    assert "✓ Месяц" in _texts(markup)


async def test_legacy_half_year(session: AsyncSession, cbr):
    await _track(session, "USD", "Доллар США", 504)
    message = _Message(504)
    await on_chart_legacy(_Callback("chart:period:half_year", message), session, AsyncMock())
    caption, markup = message.photos[-1]
    assert "Курсы ЦБ: Полгода" in caption
    assert "✓ Полгода" in _texts(markup)


async def test_uzs_nominal_is_normalized_before_caption(session: AsyncSession, cbr):
    await _track(session, "UZS", "Узбекских сумов", 505)
    message = _Message(505)
    await _send_chart(message, session, 240)
    caption, _markup = message.photos[0]
    assert "UZS (за 10K)" in caption
    assert "<b>106.53</b>" in caption
    assert "10.65" not in caption


async def test_missing_currency_is_no_data(session: AsyncSession, cbr):
    await _track(session, "XYZ", "Неизвестная", 506)
    message = _Message(506)
    before = _metric(chart_errors_total, reason="no_data")
    await _send_chart(message, session, 1)
    assert message.photos == []
    assert "Нет данных ЦБ" in message.texts[0]
    assert _metric(chart_errors_total, reason="no_data") == before + 1


async def test_cbr_failure_is_reported(session: AsyncSession, monkeypatch):
    await _track(session, "USD", "Доллар США", 507)

    async def fetch(endpoint, url, params=None):
        raise RuntimeError("cbr down")

    monkeypatch.setattr("clients.cbr._fetch_cbr_text", fetch)
    message = _Message(507)
    before = _metric(chart_errors_total, reason="cbr")
    await _send_chart(message, session, 1)
    assert message.photos == []
    assert "Не удалось получить курсы ЦБ" in message.texts[0]
    assert _metric(chart_errors_total, reason="cbr") == before + 1


async def test_edit_failure_sends_new_photo(session: AsyncSession, cbr):
    await _track(session, "USD", "Доллар США", 508)
    message = _Message(508)
    message.edit_error = RuntimeError("edit")
    before = chart_edit_failures_total._value.get()
    await on_chart_span(_Callback("chart:span:1", message), session, AsyncMock())
    assert chart_edit_failures_total._value.get() == before + 1
    caption, markup = message.photos[-1]
    assert "Курсы ЦБ: Неделя" in caption
    assert "✓ Неделя" in _texts(markup)
