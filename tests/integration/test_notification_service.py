import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.services.notification_service import (
    NotificationNotFoundError,
    list_unread,
    mark_read,
    notify_lead_assigned,
    notify_new_lead,
)


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_broadcast_notification_visible_to_any_admin(session):
    notify_new_lead(session, lead_id="lead-1", service_key="kitchen_remodeling", city="South Bend")
    session.commit()

    unread_for_admin_a = list_unread(session, admin_id="admin-a")
    unread_for_admin_b = list_unread(session, admin_id="admin-b")
    assert len(unread_for_admin_a) == 1
    assert len(unread_for_admin_b) == 1


def test_targeted_notification_only_visible_to_recipient(session):
    notify_lead_assigned(session, admin_id="admin-a", lead_id="lead-1", public_reference="GB-ABC123")
    session.commit()

    assert len(list_unread(session, admin_id="admin-a")) == 1
    assert len(list_unread(session, admin_id="admin-b")) == 0


def test_mark_read_removes_from_unread_list(session):
    n = notify_new_lead(session, lead_id="lead-1", service_key="roof_repair", city=None)
    session.commit()

    mark_read(session, notification_id=n.id)
    session.commit()

    assert list_unread(session, admin_id="any-admin") == []


def test_mark_read_nonexistent_raises(session):
    with pytest.raises(NotificationNotFoundError):
        mark_read(session, notification_id="does-not-exist")
