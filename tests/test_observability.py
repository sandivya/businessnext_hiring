from __future__ import annotations

import io
import json
import logging

from businessnext_agent.infrastructure.observability import (
    JsonLogFormatter,
    configure_structured_logging,
    current_log_context,
    log_context,
    new_request_id,
)


def test_json_log_formatter_adds_context_extras_and_exception() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("businessnext.tests.observability")
    old_handlers = logger.handlers
    old_level = logger.level
    old_propagate = logger.propagate
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        with log_context(request_id="REQ1", session_id="S1", trace_id=None):
            logger.info("hello %s", "world", extra={"operation": "unit.test", "latency_ms": 12})
            try:
                raise ValueError("broken")
            except ValueError:
                logger.exception("failed", extra={"error_type": "ValueError"})
        assert current_log_context() == {}
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate

    info_line, error_line = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert info_line["message"] == "hello world"
    assert info_line["request_id"] == "REQ1"
    assert info_line["session_id"] == "S1"
    assert info_line["operation"] == "unit.test"
    assert info_line["latency_ms"] == 12
    assert "trace_id" not in info_line
    assert error_line["error_type"] == "ValueError"
    assert "ValueError: broken" in error_line["exception"]


def test_configure_structured_logging_and_request_id() -> None:
    root = logging.getLogger()
    old_handlers = root.handlers
    old_level = root.level
    try:
        configure_structured_logging("DEBUG")
        assert root.level == logging.DEBUG
        assert isinstance(root.handlers[0].formatter, JsonLogFormatter)
        assert new_request_id()
    finally:
        root.handlers = old_handlers
        root.setLevel(old_level)
