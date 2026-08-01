"""Callback and consultation requests. Never implies a guaranteed/confirmed
appointment on creation — status starts at "requested" and only an admin
action moves it to "confirmed" (see spec §18: never guarantee appointments).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppointmentType(str, enum.Enum):
    CALLBACK = "callback"
    CONSULTATION = "consultation"


class AppointmentStatus(str, enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    appointment_type: Mapped[AppointmentType] = mapped_column(
        Enum(AppointmentType, native_enum=False, length=16)
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, native_enum=False, length=16), default=AppointmentStatus.REQUESTED
    )

    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    requested_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO date, YYYY-MM-DD
    time_window: Mapped[str | None] = mapped_column(String(16), nullable=True)  # morning/afternoon/evening/any_time
    customer_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
