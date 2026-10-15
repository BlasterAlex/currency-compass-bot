import logging

from bot.log_filter import (
    _HANDLER_TRANSPORT_GRACE_S,
    _POLLING_ALERT_AFTER_S,
    TransientPollingFilter,
)


class TelegramNetworkError(Exception):
    pass


class TelegramServerError(Exception):
    pass


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _record(
    name: str,
    message: str,
    level: int = logging.ERROR,
    exc: BaseException | None = None,
) -> logging.LogRecord:
    exc_info = (type(exc), exc, None) if exc is not None else None
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


def _filter() -> tuple[TransientPollingFilter, _Clock]:
    clock = _Clock()
    return TransientPollingFilter(clock=clock), clock


def _level(record: logging.LogRecord) -> str:
    return logging.getLevelName(record.levelno)


def test_single_transient_polling_errors_are_warnings():
    messages = (
        "Failed to fetch updates - TelegramRetryAfter: Flood control",
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
        "Failed to fetch updates - TelegramServerError: Telegram server says - Bad Gateway",
    )
    for message in messages:
        log_filter, _clock = _filter()
        record = _record("aiogram.dispatcher", message)
        assert log_filter.filter(record) is True
        assert _level(record) == "WARNING"


def test_other_polling_failures_stay_errors():
    log_filter, _clock = _filter()
    record = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramUnauthorizedError: Unauthorized",
    )
    log_filter.filter(record)
    assert _level(record) == "ERROR"


def test_outage_alerts_once_then_stays_quiet_until_reconnect():
    log_filter, clock = _filter()
    first = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramServerError: Telegram server says - Bad Gateway",
    )
    log_filter.filter(first)
    assert _level(first) == "WARNING"

    clock.now = _POLLING_ALERT_AFTER_S - 1
    still_short = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
    )
    log_filter.filter(still_short)
    assert _level(still_short) == "WARNING"

    clock.now = _POLLING_ALERT_AFTER_S
    alert = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
    )
    log_filter.filter(alert)
    assert _level(alert) == "ERROR"
    assert alert.getMessage().startswith(f"Telegram polling unavailable for {_POLLING_ALERT_AFTER_S:.0f}s:")

    clock.now = _POLLING_ALERT_AFTER_S + 30
    later = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
    )
    log_filter.filter(later)
    assert _level(later) == "WARNING"

    clock.now = _POLLING_ALERT_AFTER_S + 40
    log_filter.filter(_record("aiogram.dispatcher", "Connection established (tryings = 6, bot id = 1)"))

    clock.now = _POLLING_ALERT_AFTER_S + 41
    after = _record(
        "aiogram.dispatcher",
        "Failed to fetch updates - TelegramServerError: Telegram server says - Bad Gateway",
    )
    log_filter.filter(after)
    assert _level(after) == "WARNING"


def test_handler_transport_error_is_suppressed_only_as_outage_tail():
    log_filter, clock = _filter()
    bare = _record(
        "aiogram.event",
        "Cause exception while process update id=1 by bot id=2",
        exc=TelegramNetworkError("Request timeout error"),
    )
    log_filter.filter(bare)
    assert _level(bare) == "ERROR"

    log_filter.filter(
        _record(
            "aiogram.dispatcher",
            "Failed to fetch updates - TelegramServerError: Telegram server says - Bad Gateway",
        )
    )
    clock.now = _POLLING_ALERT_AFTER_S
    log_filter.filter(
        _record(
            "aiogram.dispatcher",
            "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
        )
    )

    during = _record(
        "aiogram.event",
        "Cause exception while process update id=2 by bot id=2",
        exc=TelegramServerError("Bad Gateway"),
    )
    log_filter.filter(during)
    assert _level(during) == "WARNING"

    bug = _record(
        "aiogram.event",
        "Cause exception while process update id=3 by bot id=2",
        exc=RuntimeError("bug"),
    )
    log_filter.filter(bug)
    assert _level(bug) == "ERROR"

    clock.now = _POLLING_ALERT_AFTER_S + 10
    log_filter.filter(_record("aiogram.dispatcher", "Connection established (tryings = 4, bot id = 1)"))

    tail = _record(
        "aiogram.event",
        "Cause exception while process update id=4 by bot id=2",
        exc=TelegramNetworkError("Request timeout error"),
    )
    log_filter.filter(tail)
    assert _level(tail) == "WARNING"

    clock.now = _POLLING_ALERT_AFTER_S + 10 + _HANDLER_TRANSPORT_GRACE_S
    after_grace = _record(
        "aiogram.event",
        "Cause exception while process update id=5 by bot id=2",
        exc=TelegramNetworkError("Request timeout error"),
    )
    log_filter.filter(after_grace)
    assert _level(after_grace) == "ERROR"


def test_short_blip_does_not_hide_a_later_handler_error():
    log_filter, clock = _filter()
    log_filter.filter(
        _record(
            "aiogram.dispatcher",
            "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error",
        )
    )
    clock.now = 15
    log_filter.filter(_record("aiogram.dispatcher", "Connection established (tryings = 1, bot id = 1)"))

    record = _record(
        "aiogram.event",
        "Cause exception while process update id=9 by bot id=2",
        exc=TelegramNetworkError("Request timeout error"),
    )
    log_filter.filter(record)
    assert _level(record) == "ERROR"
