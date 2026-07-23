"""Centralized structured logging configuration."""

import logging
import sys
from typing import Any

from app.core.config import get_settings

# Fields that must never appear in logs
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "secret",
        "secret_key",
        "jwt_secret_key",
        "email_body",
        "html_body",
        "document_content",
        "api_key",
        "client_secret",
    }
)


class SensitiveDataFilter(logging.Filter):
    """Redact sensitive values from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {k: self._redact(k, v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            # Avoid mutating unexpected formats; message formatting stays safe
            pass
        if hasattr(record, "msg") and isinstance(record.msg, dict):
            record.msg = {k: self._redact(k, v) for k, v in record.msg.items()}
        return True

    @staticmethod
    def _redact(key: str, value: Any) -> Any:
        if key.lower() in SENSITIVE_KEYS:
            return "***REDACTED***"
        return value


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())
    root.addHandler(handler)

    # Quiet noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
