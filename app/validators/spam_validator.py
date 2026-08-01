"""Lightweight spam/abuse signals for lead submissions: honeypot field and
a couple of cheap content heuristics. This is intentionally simple — a full
scoring model or third-party spam service is out of scope for this phase.
"""
from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
MAX_URLS_IN_DESCRIPTION = 2


def check_spam(payload: dict) -> ValidationResult:
    if payload.get("honeypot"):
        # A hidden field real customers never see or fill; only bots
        # (which fill every field) trip this.
        return fail("spam_honeypot_triggered", "Submission blocked.")

    description = payload.get("project_description") or ""
    url_count = len(_URL_PATTERN.findall(description))
    if url_count > MAX_URLS_IN_DESCRIPTION:
        return fail("spam_excessive_links", "Please remove links from the project description and try again.")

    return ok("no_spam_detected")
