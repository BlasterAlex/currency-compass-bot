import logging
import time
from collections.abc import Callable

_POLLING_ALERT_AFTER_S = 120.0
_HANDLER_TRANSPORT_GRACE_S = 180.0

_TRANSIENT_POLLING_MARKERS = (
    "Failed to fetch updates - TelegramRetryAfter",
    "Failed to fetch updates - TelegramNetworkError",
    "Failed to fetch updates - TelegramServerError",
)
_TRANSPORT_EXC_NAMES = frozenset(
    {
        "TelegramRetryAfter",
        "TelegramNetworkError",
        "TelegramServerError",
    }
)


def _downgrade(record: logging.LogRecord) -> None:
    record.levelno = logging.WARNING
    record.levelname = "WARNING"


def _is_transport_exc(record: logging.LogRecord) -> bool:
    if not record.exc_info or record.exc_info[1] is None:
        return False
    return type(record.exc_info[1]).__name__ in _TRANSPORT_EXC_NAMES


class TransientPollingFilter(logging.Filter):
    """Drop short GetUpdates blips. Page once when polling stays down.

    TelegramRetryAfter, network timeouts and 5xx on getUpdates are retried by
    aiogram. They stay at WARNING until the streak lasts
    `_POLLING_ALERT_AFTER_S`, then one ERROR is kept. The rest of that outage
    stays at WARNING until `Connection established`.

    A handler failure caused by the same Telegram transport errors is lowered
    while that outage is open and for `_HANDLER_TRANSPORT_GRACE_S` after
    reconnect, so the tail (for example a sendPhoto timeout) does not page
    again. The same exception with healthy polling stays at ERROR.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        super().__init__()
        self._now = clock or time.monotonic
        self._outage_started_at: float | None = None
        self._alerted = False
        self._suppress_handler_until = 0.0

    def filter(self, record: logging.LogRecord) -> bool:
        now = self._now()
        message = record.getMessage()

        if record.name == "aiogram.dispatcher" and "Connection established" in message:
            if self._alerted:
                self._suppress_handler_until = now + _HANDLER_TRANSPORT_GRACE_S
            self._outage_started_at = None
            self._alerted = False
            return True

        if self._is_transient_polling(record, message):
            if self._outage_started_at is None:
                self._outage_started_at = now
            elapsed = now - self._outage_started_at
            if not self._alerted and elapsed >= _POLLING_ALERT_AFTER_S:
                self._alerted = True
                record.msg = f"Telegram polling unavailable for {elapsed:.0f}s: {message}"
                record.args = ()
                return True
            _downgrade(record)
            return True

        if (
            record.levelno >= logging.ERROR
            and record.name == "aiogram.event"
            and "Cause exception while process update" in message
            and _is_transport_exc(record)
            and (self._alerted or now < self._suppress_handler_until)
        ):
            _downgrade(record)
        return True

    @staticmethod
    def _is_transient_polling(record: logging.LogRecord, message: str) -> bool:
        return (
            record.name == "aiogram.dispatcher"
            and record.levelno >= logging.ERROR
            and any(marker in message for marker in _TRANSIENT_POLLING_MARKERS)
        )
