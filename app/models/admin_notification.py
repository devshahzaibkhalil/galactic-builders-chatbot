"""Internal admin dashboard notifications (the BellRing icon in the nav).
Distinct from EmailNotification, which is customer/admin email delivery —
this is purely for the in-app notification bell.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Null recipient_admin_id = broadcast to every admin/superadmin (e.g.
    # "new lead received"); set = targeted (e.g. "a lead was assigned to you").
    recipient_admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    notification_type: Mapped[str] = mapped_column(String(32))  # "new_lead" | "lead_assigned" | "overdue_followup"
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g. "lead"
    related_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
