"""Records a customer question the chatbot could not confidently answer.
Reviewed by admins in the Knowledge Improvement Inbox (spec 16.9) — an
admin links an approved FAQ and marks it resolved; nothing here is ever
auto-published (see knowledge_improvement_service.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UnknownQuery(Base):
    __tablename__ = "unknown_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    message: Mapped[str] = mapped_column(Text)
    attempted_service_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempted_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_by_admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_faq_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_service_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
