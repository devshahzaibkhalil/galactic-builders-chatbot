"""Formats the final text sent to the widget.

Kept deliberately thin — this module composes strings, it does not decide
what content goes into the response (that's chat_engine's job).
"""
from __future__ import annotations

from typing import Optional


def side_question_response(answer_text: str, repeated_prompt: Optional[str]) -> str:
    """Answers the side question, then re-asks whatever field was pending —
    per spec: never drop the active flow because the customer asked something."""
    if not repeated_prompt:
        return answer_text
    return f"{answer_text}\n\nContinuing your estimate request, {repeated_prompt.rstrip('?')}?"


def service_offer_response(summary: str) -> str:
    return summary


def compose(*parts: str) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())
