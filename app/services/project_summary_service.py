"""Builds the editable Project Snapshot shown before interest confirmation.

Read-only projection over the in-progress lead/conversation state. Editing
happens by the customer sending a field update back through the estimate
flow (flow_manager.py) — this module only renders the summary, it never
mutates state itself.
"""
from __future__ import annotations

from typing import Any, TypedDict


class SnapshotField(TypedDict):
    label: str
    value: str | None
    editable: bool


class ProjectSnapshot(TypedDict):
    fields: list[SnapshotField]


_FIELD_LABELS: list[tuple[str, str]] = [
    ("service_key", "Service"),
    ("project_description", "Project description"),
    ("city", "City"),
    ("state", "State"),
    ("zip_code", "ZIP code"),
    ("timeline", "Timeline"),
    ("budget_range", "Budget range"),
    ("preferred_contact_method", "Preferred contact method"),
    ("photo_count", "Uploaded files"),
]


def build_snapshot(lead_data: dict[str, Any]) -> ProjectSnapshot:
    fields: list[SnapshotField] = []
    for key, label in _FIELD_LABELS:
        value = lead_data.get(key)
        display_value = str(value) if value not in (None, "") else "Not provided"
        fields.append({"label": label, "value": display_value, "editable": True})
    return {"fields": fields}
