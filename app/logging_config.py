"""Structured JSON logging, with every record's message and args passed
through app/security/redaction.py before formatting. This is what makes
redaction.py actually apply in practice — attaching the filter here means
no call site has to remember to redact anything itself.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.security.redaction import redact


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Idempotent — safe to call more than once (e.g. once per test app).
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
