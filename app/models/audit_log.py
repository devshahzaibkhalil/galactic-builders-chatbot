"""Audit log entries. Append-only by convention — no update/delete method
exists anywhere in this codebase for this model; rows are written once by
audit_service.record() and only ever read back.
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


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # admin_users.id; nullable because some actions are system-initiated.
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)  # e.g. "knowledge.publish", "auth.login_failed"
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "service_faq_file", "lead"
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    @property
    def metadata_dict(self) -> dict:
        try:
            return json.loads(self.metadata_json)
        except (TypeError, ValueError):
            return {}
