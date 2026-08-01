"""Records audit events. Every module that needs to log an admin/system
action calls audit_service.record() — nothing else writes an AuditLog row
directly (see audit_repository.py docstring).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories import audit_repository


def record(
    session: Session,
    *,
    action: str,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    return audit_repository.insert(session, entry)


def history_for(session: Session, *, target_type: str, target_id: str) -> list[AuditLog]:
    return audit_repository.list_for_target(session, target_type=target_type, target_id=target_id)
