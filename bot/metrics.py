"""Prometheus metrics for alerts. Low cardinality: command, endpoint, result."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Gauge, Histogram

cbr_requests_total = Counter(
    "cbr_requests_total",
    "Запросы к скриптам ЦБ",
    labelnames=("endpoint", "result"),
)
cbr_request_duration_seconds = Histogram(
    "cbr_request_duration_seconds",
    "Длительность запроса к ЦБ",
    labelnames=("endpoint",),
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)
cbr_last_success_timestamp_seconds = Gauge(
    "cbr_last_success_timestamp_seconds",
    "Unix-время последнего успешного ответа ЦБ",
    labelnames=("endpoint",),
)

db_errors_total = Counter(
    "db_errors_total",
    "Ошибки сессии или запроса PostgreSQL",
)

bot_commands_total = Counter(
    "bot_commands_total",
    "Исходы команд бота",
    labelnames=("command", "result"),
)
bot_command_duration_seconds = Histogram(
    "bot_command_duration_seconds",
    "Длительность обработки команды",
    labelnames=("command",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 15),
)

chart_builds_total = Counter(
    "chart_builds_total",
    "Собранные графики",
    labelnames=("period",),
)
chart_errors_total = Counter(
    "chart_errors_total",
    "Ошибки сборки графика",
    labelnames=("reason",),
)
chart_series_missing_total = Counter(
    "chart_series_missing_total",
    "Валюты пользователя без ряда ЦБ",
)
chart_render_duration_seconds = Histogram(
    "chart_render_duration_seconds",
    "Длительность отрисовки PNG",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
chart_edit_failures_total = Counter(
    "chart_edit_failures_total",
    "Не удалось заменить фото графика",
)


class CommandTrack:
    def __init__(self) -> None:
        self.result = "ok"


@contextmanager
def track_command(command: str) -> Iterator[CommandTrack]:
    track = CommandTrack()
    started = time.perf_counter()
    try:
        yield track
    except Exception:
        if track.result == "ok":
            track.result = "error"
        raise
    finally:
        bot_commands_total.labels(command=command, result=track.result).inc()
        bot_command_duration_seconds.labels(command=command).observe(time.perf_counter() - started)


def record_cbr_fetch(endpoint: str, result: str, elapsed: float) -> None:
    cbr_requests_total.labels(endpoint=endpoint, result=result).inc()
    cbr_request_duration_seconds.labels(endpoint=endpoint).observe(elapsed)
    if result == "ok":
        cbr_last_success_timestamp_seconds.labels(endpoint=endpoint).set(time.time())
