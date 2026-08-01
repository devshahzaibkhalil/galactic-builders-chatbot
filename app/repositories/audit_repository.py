"""Database operations for AuditLog. Owns queries only — no business rules,
no decision about *what* to log (that's audit_service.py).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def insert(session: Session, entry: AuditLog) -> AuditLog:
    session.add(entry)
    session.flush()
    return entry


def list_for_target(session: Session, *, target_type: str, target_id: str, limit: int = 50) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.target_type == target_type, AuditLog.target_id == target_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())


def list_recent(session: Session, *, action_prefix: str | None = None, limit: int = 100) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action_prefix:
        stmt = select(AuditLog).where(AuditLog.action.like(f"{action_prefix}%")).order_by(
            AuditLog.created_at.desc()
        ).limit(limit)
    return list(session.execute(stmt).scalars())
