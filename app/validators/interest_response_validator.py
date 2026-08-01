"""Validates and normalizes the customer's response to the mandatory
interest-confirmation step:

    "Kindly confirm your interest in moving forward with this opportunity."

This is the single authoritative place that decides whether free text counts
as Yes, No, or neither. Do not duplicate this matching logic in chat_engine,
routes, or JavaScript.
"""
from __future__ import annotations

import re
from typing import TypedDict

_YES_VALUES = {"yes", "y", "yeah", "sure", "continue", "move forward"}
_NO_VALUES = {"no", "n", "not now", "stop", "cancel"}

_PROMPT_TEXT = "Please select Yes or No to confirm whether you want to move forward."


class InterestValidationResult(TypedDict):
    valid: bool
    normalized_value: str | None  # "yes" | "no" | None
    error_code: str | None
    message: str | None


def _normalize_raw(text: str) -> str:
    return re.sub(r"[^a-z\s]", "", text.strip().lower()).strip()


def validate_interest_response(raw_text: str, *, from_button: bool = False) -> InterestValidationResult:
    """Validate a candidate Yes/No response.

    from_button=True should be passed when the value came from the actual
    Yes/No buttons (quick_actions.json interest_confirmation options), in
    which case the value is trusted directly rather than pattern-matched.
    """
    if from_button:
        normalized = raw_text.strip().lower()
        if normalized in ("yes", "no"):
            return {
                "valid": True,
                "normalized_value": normalized,
                "error_code": None,
                "message": None,
            }
        return {
            "valid": False,
            "normalized_value": None,
            "error_code": "invalid_button_value",
            "message": _PROMPT_TEXT,
        }

    normalized = _normalize_raw(raw_text)

    if not normalized:
        return {
            "valid": False,
            "normalized_value": None,
            "error_code": "empty_response",
            "message": _PROMPT_TEXT,
        }

    # Only accept an exact match against the allowed vocabulary. A message
    # that merely contains "yes"/"no" as a substring of an unrelated
    # sentence (e.g. a side question) must NOT be treated as a response —
    # that is handled upstream by side_question_detector before this
    # validator is even called.
    if normalized in _YES_VALUES:
        return {
            "valid": True,
            "normalized_value": "yes",
            "error_code": None,
            "message": None,
        }

    if normalized in _NO_VALUES:
        return {
            "valid": True,
            "normalized_value": "no",
            "error_code": None,
            "message": None,
        }

    return {
        "valid": False,
        "normalized_value": None,
        "error_code": "unclear_response",
        "message": _PROMPT_TEXT,
    }
