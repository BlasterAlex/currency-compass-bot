from unittest.mock import AsyncMock

import pytest

from bot.handlers.chart import (
    on_chart_legacy,
    on_chart_menu,
    on_chart_other,
    on_chart_pick,
    on_chart_span,
    on_chart_unit,
)
from bot.metrics import chart_errors_total


def _counter(reason: str) -> float:
    return chart_errors_total.labels(reason=reason)._value.get()


class _Message:
    def __init__(self) -> None:
        self.markups: list = []
        self.photos: list = []
        self.fail_markup = False

    async def edit_reply_markup(self, reply_markup=None, **kwargs) -> None:
        if self.fail_markup:
            raise RuntimeError("markup")
        self.markups.append(reply_markup)

    async def answer_photo(self, *args, **kwargs) -> None:
        self.photos.append(args)


class _Callback:
    def __init__(self, data: str, message: _Message | None = None) -> None:
        self.data = data
        self.message = message if message is not None else _Message()
        self.answers = 0

    async def answer(self, *args, **kwargs) -> None:
        self.answers += 1


def _texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_other_opens_units_without_building_chart():
    callback = _Callback("chart:other:4")
    await on_chart_other(callback, AsyncMock())
    assert callback.answers == 1
    assert callback.message.photos == []
    assert _texts(callback.message.markups[-1])[:3] == ["Недели", "Месяцы", "Годы"]


async def test_unit_marks_number_that_matches_window():
    callback = _Callback("chart:unit:week:4")
    await on_chart_unit(callback, AsyncMock())
    assert ("✓ 4", "chart:menu:4") in [
        (button.text, button.callback_data)
        for row in callback.message.markups[-1].inline_keyboard
        for button in row
    ]


async def test_menu_returns_quick_row():
    callback = _Callback("chart:menu:2")
    await on_chart_menu(callback, AsyncMock())
    texts = _texts(callback.message.markups[-1])
    assert "Неделя" in texts
    assert "Другой" in texts
    assert "✓ Другой" not in texts


async def test_invalid_span_counts_error_and_keeps_chart():
    callback = _Callback("chart:span:999")
    before = _counter("invalid_span")
    await on_chart_span(callback, AsyncMock(), AsyncMock())
    assert _counter("invalid_span") == before + 1
    assert callback.message.photos == []
    assert callback.message.markups == []


@pytest.mark.parametrize(
    ("handler", "data", "needs_session"),
    [
        (on_chart_legacy, "chart:period:nope", True),
        (on_chart_pick, "chart:pick:week:x", True),
        (on_chart_pick, "chart:pick:week:9", True),
        (on_chart_other, "chart:other:nope", False),
        (on_chart_unit, "chart:unit:day:1", False),
        (on_chart_unit, "chart:unit:week:999", False),
        (on_chart_menu, "chart:menu:0", False),
    ],
)
async def test_bad_callback_is_invalid_span(handler, data, needs_session):
    callback = _Callback(data)
    before = _counter("invalid_span")
    if needs_session:
        await handler(callback, AsyncMock(), AsyncMock())
    else:
        await handler(callback, AsyncMock())
    assert _counter("invalid_span") == before + 1
    assert callback.message.markups == []


async def test_rebuild_without_message_stops():
    callback = _Callback("chart:span:1")
    callback.message = None
    await on_chart_span(callback, AsyncMock(), AsyncMock())
    assert callback.answers == 1


async def test_keyboard_edit_failure_is_not_a_build_error():
    message = _Message()
    message.fail_markup = True
    callback = _Callback("chart:other:1", message)
    before = _counter("invalid_span") + _counter("cbr") + _counter("no_data") + _counter("render")
    await on_chart_other(callback, AsyncMock())
    after = _counter("invalid_span") + _counter("cbr") + _counter("no_data") + _counter("render")
    assert after == before
    assert message.photos == []
