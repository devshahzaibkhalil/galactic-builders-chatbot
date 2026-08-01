from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.unknown_query import UnknownQuery


def insert(session: Session, entry: UnknownQuery) -> UnknownQuery:
    session.add(entry)
    session.flush()
    return entry


def list_unresolved(session: Session, *, limit: int = 100) -> list[UnknownQuery]:
    stmt = (
        select(UnknownQuery)
        .where(UnknownQuery.resolved.is_(False))
        .order_by(UnknownQuery.created_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())


def get(session: Session, unknown_query_id: str) -> UnknownQuery | None:
    return session.get(UnknownQuery, unknown_query_id)
