"""Estimate Readiness Meter and Opportunity Priority Board scoring.

This is NOT a price estimate — it only measures how complete a request is,
and (separately) how it should be prioritized once submitted. Both scores
are informational for staff/customer display; neither ever auto-rejects a
lead (see spec 16.5).
"""
from __future__ import annotations

from typing import Any, TypedDict

# Weighted so "photos" and "street address" stay optional without capping
# readiness below 100%.
_READINESS_WEIGHTS: dict[str, int] = {
    "service_key": 15,
    "project_description": 15,
    "city": 10,
    "state": 5,
    "zip_code": 10,
    "timeline": 10,
    "budget_range": 10,
    "full_name": 10,
    "email": 10,
    "phone": 5,
    "preferred_contact_method": 5,
}
_TOTAL_WEIGHT = sum(_READINESS_WEIGHTS.values())  # 105 -> normalized to 100


class ReadinessBreakdown(TypedDict):
    project_details: str
    location: str
    timeline: str
    contact_details: str
    photos: str
    readiness_percent: int


def calculate_readiness(lead_data: dict[str, Any]) -> ReadinessBreakdown:
    earned = sum(weight for field, weight in _READINESS_WEIGHTS.items() if lead_data.get(field))
    percent = round(min(earned, _TOTAL_WEIGHT) / _TOTAL_WEIGHT * 100)

    def status(*fields: str) -> str:
        return "Complete" if all(lead_data.get(f) for f in fields) else "Incomplete"

    return {
        "project_details": status("service_key", "project_description"),
        "location": status("city", "state", "zip_code"),
        "timeline": status("timeline", "budget_range"),
        "contact_details": status("full_name", "email", "phone"),
        "photos": "Complete" if lead_data.get("photo_count", 0) > 0 else "Optional",
        "readiness_percent": percent,
    }


class PriorityLabel:
    PRIORITY = "Priority"
    STANDARD = "Standard"
    NEEDS_REVIEW = "Needs Review"
    INCOMPLETE = "Incomplete"


def calculate_priority_label(lead_data: dict[str, Any]) -> str:
    """Internal-only label for the Opportunity Priority Board.

    Never used to reject a lead — display/sorting only.
    """
    readiness = calculate_readiness(lead_data)
    percent = readiness["readiness_percent"]
    has_timeline = bool(lead_data.get("timeline"))
    has_callback_request = bool(lead_data.get("requested_callback"))
    has_photos = lead_data.get("photo_count", 0) > 0
    safety_flag = bool(lead_data.get("safety_flag"))

    if percent < 50:
        return PriorityLabel.INCOMPLETE

    if safety_flag or (percent >= 90 and has_timeline and (has_photos or has_callback_request)):
        return PriorityLabel.PRIORITY

    if percent >= 70:
        return PriorityLabel.STANDARD

    return PriorityLabel.NEEDS_REVIEW
