import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _unread_count(app):
    from app.services.notification_service import list_unread

    session = app.extensions["db_session_factory"]()
    try:
        return len(list_unread(session, admin_id="any-admin-id"))
    finally:
        session.close()


def test_new_conversation_with_matched_intent_triggers_exactly_one_notification(app, client):
    # "kitchen remodel" matches a real service FAQ, so this is answered
    # (not a fallback) — isolates the new_conversation trigger on its own.
    assert _unread_count(app) == 0
    client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    assert _unread_count(app) == 1


def test_second_message_in_same_conversation_does_not_trigger_new_conversation_again(app, client):
    resp = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    conversation_id = resp.get_json()["conversation_id"]
    client.post(
        "/api/chat/message",
        json={"message": "I also want a roof repair", "conversation_id": conversation_id, "session_id": "s1"},
    )
    # Still only the one new_conversation notification — a second message
    # in the SAME conversation must not fire it again.
    assert _unread_count(app) == 1


def test_appointment_request_triggers_notification(app, client):
    assert _unread_count(app) == 0
    client.post("/api/appointments", json={"appointment_type": "callback", "phone": "574-555-0100"})
    assert _unread_count(app) == 1


def test_unanswered_question_triggers_notification(app, client):
    assert _unread_count(app) == 0
    client.post("/api/chat/message", json={"message": "asdkfj qwoeiru nonsense zzz", "session_id": "s1"})
    # This message is both a new conversation AND unanswered, so both fire.
    assert _unread_count(app) == 2
