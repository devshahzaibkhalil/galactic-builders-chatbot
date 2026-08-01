import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.services.audit_service import history_for, record


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_record_creates_entry_with_metadata(session):
    entry = record(
        session,
        action="knowledge.publish",
        actor_id="admin-1",
        actor_role="admin",
        target_type="service_faq_file",
        target_id="kitchen_remodeling",
        metadata={"faq_count": 15},
    )
    session.commit()
    assert entry.id is not None
    assert entry.metadata_dict == {"faq_count": 15}


def test_history_for_target_returns_only_matching_entries(session):
    record(session, action="knowledge.publish", target_type="service_faq_file", target_id="kitchen_remodeling")
    record(session, action="knowledge.publish", target_type="service_faq_file", target_id="roof_repair")
    session.commit()

    kitchen_history = history_for(session, target_type="service_faq_file", target_id="kitchen_remodeling")
    assert len(kitchen_history) == 1
    assert kitchen_history[0].target_id == "kitchen_remodeling"


def test_system_action_allows_null_actor(session):
    entry = record(session, action="auth.login_failed", metadata={"identifier": "someone@example.com"})
    session.commit()
    assert entry.actor_id is None
