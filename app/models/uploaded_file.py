"""Uploaded project file record.

storage_name is a random token, never the customer's original filename —
prevents path traversal and makes URLs non-guessable (Secure Project Vault
requirement: no public storage links, ownership checks required to read).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

DEFAULT_EXPIRATION_DAYS = 180


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_expiration() -> datetime:
    return _utcnow() + timedelta(days=DEFAULT_EXPIRATION_DAYS)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)

    storage_name: Mapped[str] = mapped_column(String(64), unique=True)  # random, not user-controlled
    original_filename: Mapped[str] = mapped_column(String(255))  # stored for display only, never used as a path
    mime_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_default_expiration)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
