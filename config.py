import logging
import time

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file="deploy/.env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


class _Formatter(logging.Formatter):
    converter = time.gmtime
    default_msec_format = "%s.%03d UTC"


class _TransientPollingFilter(logging.Filter):
    """Downgrade expected GetUpdates blips so log noise stays low."""

    def filter(self, record: logging.LogRecord) -> bool:
        if (
            record.name == "aiogram.dispatcher"
            and record.levelno == logging.ERROR
            and "Failed to fetch updates - TelegramRetryAfter" in record.getMessage()
        ):
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(_TransientPollingFilter())
    logging.basicConfig(level=settings.LOG_LEVEL, handlers=[handler])
