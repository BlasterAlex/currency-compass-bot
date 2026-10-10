import pytest
from sqlalchemy.exc import SQLAlchemyError

from bot.metrics import (
    bot_commands_total,
    cbr_last_success_timestamp_seconds,
    cbr_requests_total,
    chart_builds_total,
    chart_edit_failures_total,
    chart_errors_total,
    chart_series_missing_total,
    db_errors_total,
    record_cbr_fetch,
    track_command,
)
from bot.middlewares.db import DbSessionMiddleware


def _counter(metric, **labels) -> float:
    return metric.labels(**labels)._value.get()


def test_record_cbr_fetch_ok_sets_timestamp():
    before = _counter(cbr_requests_total, endpoint="daily", result="ok")
    record_cbr_fetch("daily", "ok", 0.2)
    assert _counter(cbr_requests_total, endpoint="daily", result="ok") == before + 1
    assert cbr_last_success_timestamp_seconds.labels(endpoint="daily")._value.get() > 0


def test_record_cbr_fetch_http_does_not_touch_success():
    cbr_last_success_timestamp_seconds.labels(endpoint="dynamic").set(111.0)
    record_cbr_fetch("dynamic", "http", 0.1)
    assert cbr_last_success_timestamp_seconds.labels(endpoint="dynamic")._value.get() == 111.0


def test_track_command_records_result():
    before = _counter(bot_commands_total, command="rate", result="empty")
    with track_command("rate") as track:
        track.result = "empty"
    assert _counter(bot_commands_total, command="rate", result="empty") == before + 1


def test_track_command_uncaught_is_error():
    before = _counter(bot_commands_total, command="chart", result="error")
    with pytest.raises(RuntimeError):
        with track_command("chart"):
            raise RuntimeError("boom")
    assert _counter(bot_commands_total, command="chart", result="error") == before + 1


def test_chart_counters_exist():
    chart_builds_total.labels(period="week").inc()
    chart_errors_total.labels(reason="cbr").inc()
    chart_series_missing_total.inc(2)
    chart_edit_failures_total.inc()
    assert _counter(chart_builds_total, period="week") >= 1
    assert _counter(chart_errors_total, reason="cbr") >= 1
    assert chart_series_missing_total._value.get() >= 2


@pytest.mark.asyncio
async def test_db_middleware_counts_sqlalchemy_error():
    class BrokenFactory:
        def __call__(self):
            raise SQLAlchemyError("db down")

    middleware = DbSessionMiddleware(BrokenFactory())  # type: ignore[arg-type]
    before = db_errors_total._value.get()
    with pytest.raises(SQLAlchemyError):
        await middleware(lambda e, d: None, object(), {})
    assert db_errors_total._value.get() == before + 1
