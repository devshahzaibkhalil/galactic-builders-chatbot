"""Decides, for a message received while a field is pending, whether it is:

    - a navigation command ("back", "change my email", ...)
    - a side question (should be answered, then the pending prompt repeated)
    - a direct answer to the pending field

This sits ahead of field validation in the routing priority (see
core/intent_router.py docstring) — a validation error must never be shown
for a message that was actually a question.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import NamedTuple, Optional

from app.constants.conversation_commands import COMMAND_PHRASES

_QUESTION_WORDS = (
    "do you", "does", "can you", "can i", "could you", "will you",
    "how much", "how long", "how do", "how does", "what", "why",
    "is it", "are you", "when", "where", "which",
)


class MessageKind(str, Enum):
    NAVIGATION_COMMAND = "navigation_command"
    SIDE_QUESTION = "side_question"
    FIELD_ANSWER = "field_answer"


class DetectionResult(NamedTuple):
    kind: MessageKind
    command: Optional[str] = None  # set when kind == NAVIGATION_COMMAND


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _looks_like_question(text: str) -> bool:
    normalized = _normalize(text)
    if normalized.endswith("?"):
        return True
    return any(normalized.startswith(w) for w in _QUESTION_WORDS)


def detect_navigation_command(text: str) -> Optional[str]:
    normalized = _normalize(text)
    return COMMAND_PHRASES.get(normalized)


def detect(message: str, pending_field: Optional[str], field_validator=None) -> DetectionResult:
    """Classify an incoming message against the currently pending field.

    field_validator, if provided, is a callable(str) -> {"valid": bool, ...}
    (matching app.validators.validation_result.ValidationResult). It is used
    only to help decide FIELD_ANSWER vs SIDE_QUESTION when the message is
    ambiguous — a message that both looks like a question AND fails
    validation is treated as a side question, never as an invalid answer.
    """
    command = detect_navigation_command(message)
    if command:
        return DetectionResult(MessageKind.NAVIGATION_COMMAND, command=command)

    if not pending_field:
        # No active field to answer — nothing to disambiguate against.
        return DetectionResult(MessageKind.SIDE_QUESTION if _looks_like_question(message) else MessageKind.FIELD_ANSWER)

    if _looks_like_question(message):
        return DetectionResult(MessageKind.SIDE_QUESTION)

    if field_validator is not None:
        result = field_validator(message)
        if not result.get("valid", False):
            # Doesn't look like a question, but also isn't a valid answer —
            # still treat as a field answer so the caller can show the
            # field's own validation error message (not a generic fallback).
            return DetectionResult(MessageKind.FIELD_ANSWER)

    return DetectionResult(MessageKind.FIELD_ANSWER)
