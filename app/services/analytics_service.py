"""Records feature-usage events and provides simple aggregate counts for
an admin analytics view. No individual customer tracking or PII — this is
strictly "how many times did X happen", not "who did X".
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feature_event import FeatureEvent


def track_event(
    session: Session, *, event_name: str, conversation_id: Optional[str] = None, metadata: Optional[dict] = None
) -> FeatureEvent:
    event = FeatureEvent(
        event_name=event_name,
        conversation_id=conversation_id,
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    session.add(event)
    session.flush()
    return event


def count_events(session: Session, *, event_name: str, since_days: Optional[int] = None) -> int:
    stmt = select(func.count()).select_from(FeatureEvent).where(FeatureEvent.event_name == event_name)
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        stmt = stmt.where(FeatureEvent.created_at >= cutoff)
    return session.execute(stmt).scalar_one()


def event_summary(session: Session, *, since_days: Optional[int] = None) -> dict[str, int]:
    """Returns {event_name: count} for every distinct event in the window
    — what an admin analytics dashboard would render as a simple bar list."""
    stmt = select(FeatureEvent.event_name, func.count()).group_by(FeatureEvent.event_name)
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        stmt = stmt.where(FeatureEvent.created_at >= cutoff)
    rows = session.execute(stmt).all()
    return {name: count for name, count in rows}
