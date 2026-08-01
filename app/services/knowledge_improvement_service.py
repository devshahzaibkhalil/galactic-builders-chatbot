"""Knowledge Improvement Inbox (spec 16.9).

Logs low-confidence/unanswered questions and lets an admin review them —
see the FAQ, the attempted intent, and the confidence — then either link an
already-published FAQ or mark it resolved after adding one through the
normal knowledge-publishing flow. This module NEVER auto-publishes an
answer; resolving here only records that a human made a decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.unknown_query import UnknownQuery
from app.repositories import unknown_query_repository
from app.security.permissions import require_permission
from app.services.audit_service import record as record_audit
from app.services.notification_service import notify_unanswered_question


def log_unknown_query(
    session: Session,
    *,
    message: str,
    attempted_service_key: Optional[str] = None,
    attempted_intent: Optional[str] = None,
    confidence: float = 0.0,
    conversation_id: Optional[str] = None,
) -> UnknownQuery:
    entry = UnknownQuery(
        message=message,
        attempted_service_key=attempted_service_key,
        attempted_intent=attempted_intent,
        confidence=confidence,
        conversation_id=conversation_id,
    )
    result = unknown_query_repository.insert(session, entry)
    notify_unanswered_question(session, unknown_query_id=result.id, message=message)
    return result


def list_unresolved(session: Session) -> list[UnknownQuery]:
    return unknown_query_repository.list_unresolved(session)


class UnknownQueryNotFoundError(LookupError):
    pass


def mark_resolved(
    session: Session,
    *,
    unknown_query_id: str,
    admin_id: str,
    admin_role: str,
    linked_faq_id: Optional[str] = None,
    linked_service_key: Optional[str] = None,
) -> UnknownQuery:
    """An admin/superadmin reviews an entry and marks it handled — either
    because they added an approved FAQ for it (link the id) or decided no
    FAQ change was needed."""
    require_permission(admin_role, "manage_faqs")

    entry = unknown_query_repository.get(session, unknown_query_id)
    if entry is None:
        raise UnknownQueryNotFoundError(f"No unknown query with id '{unknown_query_id}'.")

    entry.resolved = True
    entry.resolved_by_admin_id = admin_id
    entry.linked_faq_id = linked_faq_id
    entry.linked_service_key = linked_service_key
    entry.resolved_at = datetime.now(timezone.utc)

    record_audit(
        session,
        action="knowledge_inbox.resolve",
        actor_id=admin_id,
        actor_role=admin_role,
        target_type="unknown_query",
        target_id=entry.id,
        metadata={"linked_faq_id": linked_faq_id, "linked_service_key": linked_service_key},
    )
    return entry
