import json
import logging
import sys

from backend.core.config import settings


class _JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production log aggregation (ELK, Cloud Logging, etc.)."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class _TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for the given module name.

    Uses structured JSON output in production and human-readable text in
    development. Idempotent — safe to call multiple times for the same name.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if settings.ENVIRONMENT == "production":
            handler.setFormatter(_JSONFormatter())
        else:
            handler.setFormatter(_TextFormatter())
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger
