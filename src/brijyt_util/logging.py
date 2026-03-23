"""Centralized JSON logging with correlation ID and context vars."""

import json
import logging
import logging.config
import os
import traceback
from collections import OrderedDict
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context for correlation ID and other bindings (e.g. message_id)
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
_log_context_var: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def get_correlation_id() -> str:
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id_var.set(correlation_id)


def bind_contextvars(**kwargs: Any) -> None:
    ctx = _log_context_var.get().copy()
    ctx.update(kwargs)
    _log_context_var.set(ctx)


def unbind_contextvars(*keys: str) -> None:
    ctx = _log_context_var.get().copy()
    for k in keys:
        ctx.pop(k, None)
    _log_context_var.set(ctx)


def get_log_context() -> dict[str, Any]:
    """Return current log context (correlationId + any bound context vars)."""
    return {"correlationId": get_correlation_id(), **_log_context_var.get()}


# Standard LogRecord attribute names (used to exclude from extra merge)
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "process", "processName", "message", "getMessage", "taskName",
    }
)


class CustomJSONLog(logging.Formatter):
    """
    JSON formatter. Outputs: @timestamp, level, msg, method, correlationId, version, then extra/context.
    """

    def __init__(self, api_version: str) -> None:
        super().__init__()
        self.api_version = api_version
        self._order = {
            "@timestamp": 0,
            "level": 1,
            "msg": 2,
            "method": 3,
            "correlationId": 4,
            "version": 5,
            "stacktrace": 6,
        }

    def format(self, record: logging.LogRecord) -> str:
        method = f"{record.module}.{record.funcName}"
        json_log: dict[str, Any] = {
            "@timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "method": method,
            "correlationId": get_correlation_id(),
            "version": self.api_version,
        }

        # Merge context (bind_contextvars)
        for key, value in _log_context_var.get().items():
            json_log[key] = value

        # Merge record extra (kwargs from logger.info("msg", key=val))
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS:
                json_log[key] = value

        if record.exc_info:
            json_log["stacktrace"] = traceback.format_exc(limit=None)

        ordered = OrderedDict(
            sorted(json_log.items(), key=lambda x: self._order.get(x[0], 99))
        )
        return json.dumps(ordered, default=str)


def _build_context_dict(record: logging.LogRecord) -> dict[str, Any]:
    """Build context dict: correlationId, bound context vars, and record extra (for ConsoleLog)."""
    ctx: dict[str, Any] = {"correlationId": get_correlation_id()}
    for key, value in _log_context_var.get().items():
        ctx[key] = value
    for key, value in record.__dict__.items():
        if key not in _STANDARD_RECORD_ATTRS:
            ctx[key] = value
    return ctx


class ConsoleLog(logging.Formatter):
    """
    Single-line human-readable formatter: HH:MM:SS LEVEL message contextVar: {}.
    Optional stacktrace on the next line when an exception is logged.
    """

    def __init__(self, api_version: str = "") -> None:
        super().__init__()
        self.api_version = api_version

    def format(self, record: logging.LogRecord) -> str:
        time_str = datetime.now(UTC).strftime("%H:%M:%S")
        level = record.levelname
        msg = record.getMessage()
        context = _build_context_dict(record)
        context_str = json.dumps(context, default=str)
        line = f"{time_str} {level} {msg} contextVar: {context_str}"
        if record.exc_info:
            line += "\n" + traceback.format_exc(limit=None)
        return line


def _sanitize_extra(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Prefix keys that conflict with LogRecord attributes so extra can be stored."""
    out: dict[str, Any] = {}
    for k, v in kwargs.items():
        if k in _STANDARD_RECORD_ATTRS:
            out[f"extra_{k}"] = v
        else:
            out[k] = v
    return out


class LoggerAdapter:
    """Adapter so callers can use logger.info('msg', key=val) like structlog."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, extra=_sanitize_extra(kwargs))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(msg, *args, extra=_sanitize_extra(kwargs))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, extra=_sanitize_extra(kwargs))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(msg, *args, extra=_sanitize_extra(kwargs))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, extra=_sanitize_extra(kwargs))


def configure_logging(api_version: str) -> None:
    """Configure logging for the app package. Use LOG_FORMAT=console or human for readable one-line output."""

    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = (os.getenv("LOG_FORMAT") or "json").strip().lower()

    formatter_name = "console" if log_format in ("console", "human") else "standard"
    log_config = {
        "version": 1,
        "formatters": {
            "standard": {
                "()": CustomJSONLog,
                "api_version": api_version,
            },
            "console": {
                "()": ConsoleLog,
                "api_version": api_version,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level_str,
                "formatter": formatter_name,
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "level": logging.WARNING,
                "handlers": [],
            },
            "app": {
                "level": log_level_str,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(log_config)

    # Reduce noise from third-party loggers (they use root or their own loggers)
    for logger_name in (
        "uvicorn.access",
        "uvicorn.error",
        "crewai",
        "LiteLLM",
        "unstructured_inference",
        "openai",
        "openai._base_client",
        "pikepdf",
        "transformers",
        "timm",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> LoggerAdapter:
    """
    Return a logger for the given module name.
    Use as: logger.info("message", key=value).
    """
    return LoggerAdapter(logging.getLogger(name))
