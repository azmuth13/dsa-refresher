"""Structured JSON logging configuration for the DSA Refresher backend.

Every log record is emitted as a single JSON line with consistent fields so
that log aggregators (e.g. Datadog, Loki, CloudWatch) can index and filter
without regex parsing.

Fields always present
---------------------
timestamp   ISO-8601 UTC timestamp
level       DEBUG / INFO / WARNING / ERROR / CRITICAL
logger      dotted module name (e.g. services.llm_service)
message     human-readable summary
request_id  UUID injected by the request middleware (empty string outside a
            request context)

Optional fields added by callers via the `extra=` kwarg
---------------------------------------------------------
provider    LLM provider name (groq / gemini)
model       LLM model identifier
attempt     retry attempt number (1-indexed)
status_code HTTP status returned to the client
method      HTTP verb
path        request path
duration_ms wall-clock time in milliseconds
slug        LeetCode problem slug
url         external URL being fetched
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Request-ID context variable
# The ASGI middleware writes a UUID here at the start of every request so
# that every log line within that request carries the same ID.
# ---------------------------------------------------------------------------
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class _JsonFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object."""

    # Fields that are set by LogRecord itself and would be redundant / noisy
    # if we included them in the `extra` blob.
    _SKIP = frozenset(
        {
            "args",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "taskName",
            "thread",
            "threadName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "request_id": request_id_var.get(""),
        }

        # Attach any extra fields the caller passed via extra={}
        for key, value in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                payload[key] = value

        # Attach exception traceback as a string so it stays on one JSON line
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output.

    Call this once at application startup *before* any other logger is used.

    Parameters
    ----------
    level:
        Minimum log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        Defaults to INFO.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Remove any handlers that were added before our setup (e.g. uvicorn's
    # default handler) so we don't emit duplicate lines.
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers that would spam at DEBUG level.
    for noisy in ("httpx", "httpcore", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Structured JSON logging initialised",
        extra={"log_level": level.upper()},
    )
