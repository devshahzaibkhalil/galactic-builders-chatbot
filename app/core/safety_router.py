"""Detects high-risk safety language per spec section 17.

This check runs before everything else in the routing priority (security ->
safety -> human takeover -> active flow -> ...). It never promises emergency
attendance and never gives repair instructions — it only flags the
conversation and hands back a safety-first message.
"""
from __future__ import annotations

import re
from typing import NamedTuple

_HIGH_RISK_PATTERNS: list[str] = [
    r"gas\s+smell",
    r"smell(?:s|ing)?\s+gas",
    r"electrical\s+fire",
    r"spark(?:ing)?\s+wire",
    r"major\s+flood(?:ing)?",
    r"structural\s+collapse",
    r"roof\s+(?:is\s+)?collaps(?:ing|ed)",
    r"ceiling\s+(?:is\s+)?fall(?:ing)?",
    r"active\s+sewage",
    r"can(?:not|'t)\s+shut\s+off\s+(?:the\s+)?water",
    r"water\s+won'?t\s+shut\s+off",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _HIGH_RISK_PATTERNS]

SAFETY_FIRST_MESSAGE = (
    "This sounds like it may be a safety concern. If there is any danger to "
    "you or your property right now, please contact emergency services or "
    "the appropriate utility provider immediately.\n\n"
    "Galactic Builders cannot confirm emergency response times through this "
    "chat. A team member can follow up as soon as possible once you share a "
    "few details, but please do not wait on this chat if the situation is "
    "urgent."
)


class SafetyCheckResult(NamedTuple):
    is_safety_concern: bool
    matched_phrase: str | None
    message: str | None


def check_safety(message: str) -> SafetyCheckResult:
    for pattern in _COMPILED:
        match = pattern.search(message)
        if match:
            return SafetyCheckResult(True, match.group(0), SAFETY_FIRST_MESSAGE)
    return SafetyCheckResult(False, None, None)
