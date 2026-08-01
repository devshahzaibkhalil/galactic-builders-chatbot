import pytest

from app import create_app
from app.services.knowledge_improvement_service import list_unresolved


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_fallback_message_is_persisted_to_knowledge_inbox(app, client):
    resp = client.post(
        "/api/chat/message",
        json={"message": "asdkfj qwoeiru zzz nonsense gibberish", "session_id": "s1"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["handled_by"] == "fallback_handler"

    db_session = app.extensions["db_session_factory"]()
    try:
        unresolved = list_unresolved(db_session)
    finally:
        db_session.close()

    assert len(unresolved) == 1
    assert "gibberish" in unresolved[0].message


def test_answered_message_is_not_logged_as_unknown(app, client):
    client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})

    db_session = app.extensions["db_session_factory"]()
    try:
        unresolved = list_unresolved(db_session)
    finally:
        db_session.close()

    assert len(unresolved) == 0
