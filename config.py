import logging
import time

from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.log_filter import TransientPollingFilter


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9100

    model_config = SettingsConfigDict(env_file="deploy/.env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


class _Formatter(logging.Formatter):
    converter = time.gmtime
    default_msec_format = "%s.%03d UTC"


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(TransientPollingFilter())
    logging.basicConfig(level=settings.LOG_LEVEL, handlers=[handler])
