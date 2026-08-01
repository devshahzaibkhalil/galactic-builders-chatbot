"""Handles the lowest-priority routing branches: low-confidence fallback
and unknown-query logging.

Logging is delegated to an injected callable so this module has no direct
DB dependency yet (the `unknown_query` repository/model is a later phase).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, NamedTuple, Optional

FALLBACK_MESSAGE = (
    "I want to make sure I give you an accurate answer, and I don't have "
    "verified information for that yet. A Galactic Builders team member can "
    "follow up directly, or you can rephrase your question and I'll try again."
)

AMBIGUOUS_SERVICE_MESSAGE_TEMPLATE = (
    "I want to make sure I connect you with the right service. Did you mean "
    "{options}?"
)


class UnknownQueryRecord(NamedTuple):
    message: str
    attempted_service_key: Optional[str]
    attempted_intent: Optional[str]
    confidence: float
    logged_at: str


LogUnknownQueryFn = Callable[[UnknownQueryRecord], None]


def build_ambiguous_message(display_names: list[str]) -> str:
    if len(display_names) == 1:
        options = display_names[0]
    else:
        options = ", ".join(display_names[:-1]) + f", or {display_names[-1]}"
    return AMBIGUOUS_SERVICE_MESSAGE_TEMPLATE.format(options=options)


def handle_fallback(
    message: str,
    *,
    attempted_service_key: Optional[str] = None,
    attempted_intent: Optional[str] = None,
    confidence: float = 0.0,
    log_unknown_query: Optional[LogUnknownQueryFn] = None,
) -> str:
    record = UnknownQueryRecord(
        message=message,
        attempted_service_key=attempted_service_key,
        attempted_intent=attempted_intent,
        confidence=confidence,
        logged_at=datetime.now(timezone.utc).isoformat(),
    )
    if log_unknown_query is not None:
        log_unknown_query(record)
    return FALLBACK_MESSAGE
