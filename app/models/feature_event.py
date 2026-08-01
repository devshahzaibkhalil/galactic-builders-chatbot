"""Lightweight feature-usage event log — e.g. "estimate_flow_started",
"photo_uploaded", "bookmark_created". Intentionally minimal: no PII in the
event payload itself (conversation_id/lead_id are opaque UUIDs), used for
aggregate counts on an admin analytics view, not individual tracking.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeatureEvent(Base):
    __tablename__ = "feature_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name: Mapped[str] = mapped_column(String(64), index=True)  # e.g. "estimate_flow_started"
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    @property
    def metadata_dict(self) -> dict:
        try:
            return json.loads(self.metadata_json)
        except (TypeError, ValueError):
            return {}
