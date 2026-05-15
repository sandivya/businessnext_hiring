"""Structured logging helpers for AgentCore and local runs."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_LOG_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "businessnext_log_context",
    default=None,
)
_STANDARD_LOG_ATTRS = set(
    vars(
        logging.LogRecord(
            name="",
            level=0,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
    )
)


class JsonLogFormatter(logging.Formatter):
    """Emit compact JSON so CloudWatch can index fields without regex parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(current_log_context())
        payload.update(self._record_extras(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))

    def _record_extras(self, record: logging.LogRecord) -> dict[str, Any]:
        return {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_ATTRS and not key.startswith("_")
        }


def configure_structured_logging(level: str) -> None:
    """Configure process logging once in a format suitable for AgentCore logs."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def new_request_id() -> str:
    """Create an invocation correlation ID when no upstream ID is provided."""

    return str(uuid.uuid4())


def current_log_context() -> dict[str, Any]:
    """Return a copy so callers cannot mutate the active context."""

    return dict(_LOG_CONTEXT.get() or {})


@contextmanager
def log_context(**values: Any) -> Iterator[None]:
    """Attach request-scoped fields to every log emitted inside the block."""

    clean_values = {key: value for key, value in values.items() if value is not None}
    merged = {**current_log_context(), **clean_values}
    token = _LOG_CONTEXT.set(merged)
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)
