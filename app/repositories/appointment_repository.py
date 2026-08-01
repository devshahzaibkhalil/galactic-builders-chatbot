from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus


def insert(session: Session, appointment: Appointment) -> Appointment:
    session.add(appointment)
    session.flush()
    return appointment


def list_overdue(session: Session, *, as_of: datetime | None = None) -> list[Appointment]:
    """Appointments still 'requested' whose requested_date has already
    passed — these are what the Follow-Up Desk / Contact Window Guard
    surface as overdue on the admin dashboard."""
    as_of = as_of or datetime.now(timezone.utc)
    today_iso = as_of.date().isoformat()
    stmt = select(Appointment).where(
        Appointment.status == AppointmentStatus.REQUESTED,
        Appointment.requested_date < today_iso,
    )
    return list(session.execute(stmt).scalars())


def get(session: Session, appointment_id: str) -> Appointment | None:
    return session.get(Appointment, appointment_id)
