"""Centralized logging configuration."""

import json
import logging
from logging.config import dictConfig


class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON strings for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        data = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
             data.update(record.extra) # type: ignore
        
        # Merge extra fields from the record if they were passed via extra={...}
        # The logging module puts them directly on the record object.
        # We filter out standard LogRecord attributes to avoid clutter.
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message"
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                data[key] = value

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with JSON formatting and stdout handler."""
    dictConfig(
        {
            "version": 1,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "level": level,
                }
            },
            "root": {"handlers": ["default"], "level": level},
            "disable_existing_loggers": False,
        }
    )
