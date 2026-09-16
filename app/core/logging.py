import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for correlation ID (X-Request-ID)
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Retrieve the current request ID from context."""
    return request_id_ctx_var.get()


def set_request_id(req_id: str) -> None:
    """Set the request ID in context."""
    request_id_ctx_var.set(req_id)


class StructuredJSONFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs with correlation IDs,
    timestamps, and execution metadata.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": (
                datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request_id from context or record attribute
        req_id = get_request_id() or getattr(record, "request_id", None)
        if req_id:
            log_payload["request_id"] = req_id

        # Include any custom attributes passed in record.__dict__
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "request_id",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_payload[key] = value

        # Exception formatting
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure root logger with structured JSON or text formatting."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(StructuredJSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
    root_logger.addHandler(handler)

    # Suppress verbose loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtain a logger instance."""
    return logging.getLogger(name)
