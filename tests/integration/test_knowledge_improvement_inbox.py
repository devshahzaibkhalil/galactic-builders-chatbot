import pytest

from app.constants.roles import ADMIN, AGENT
from app.extensions import build_engine, build_session_factory, create_all
from app.security.permissions import PermissionDeniedError
from app.services.knowledge_improvement_service import (
    UnknownQueryNotFoundError,
    list_unresolved,
    log_unknown_query,
    mark_resolved,
)


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_log_unknown_query_creates_entry(session):
    entry = log_unknown_query(
        session,
        message="Do you install solar panels?",
        attempted_service_key=None,
        confidence=0.1,
        conversation_id="conv-1",
    )
    session.commit()
    assert entry.resolved is False
    assert entry.message == "Do you install solar panels?"


def test_list_unresolved_excludes_resolved_entries(session):
    log_unknown_query(session, message="Question one")
    entry2 = log_unknown_query(session, message="Question two")
    session.commit()

    mark_resolved(session, unknown_query_id=entry2.id, admin_id="admin-1", admin_role=ADMIN)
    session.commit()

    unresolved = list_unresolved(session)
    assert len(unresolved) == 1
    assert unresolved[0].message == "Question one"


def test_mark_resolved_links_faq_and_records_audit(session):
    entry = log_unknown_query(session, message="Do you do solar panel installation?")
    session.commit()

    resolved = mark_resolved(
        session,
        unknown_query_id=entry.id,
        admin_id="admin-1",
        admin_role=ADMIN,
        linked_faq_id="solar-panels-001",
        linked_service_key="solar_panel_installation",
    )
    session.commit()

    assert resolved.resolved is True
    assert resolved.linked_faq_id == "solar-panels-001"
    assert resolved.resolved_at is not None

    from app.services.audit_service import history_for
    history = history_for(session, target_type="unknown_query", target_id=entry.id)
    assert len(history) == 1
    assert history[0].action == "knowledge_inbox.resolve"


def test_agent_cannot_resolve_unknown_query(session):
    entry = log_unknown_query(session, message="Some question")
    session.commit()

    with pytest.raises(PermissionDeniedError):
        mark_resolved(session, unknown_query_id=entry.id, admin_id="agent-1", admin_role=AGENT)


def test_resolving_nonexistent_entry_raises(session):
    with pytest.raises(UnknownQueryNotFoundError):
        mark_resolved(session, unknown_query_id="does-not-exist", admin_id="admin-1", admin_role=ADMIN)
