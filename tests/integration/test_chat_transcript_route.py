import pytest

from app import create_app
from app.repositories import conversation_repository


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_chat_turn_over_http_persists_full_transcript(app, client):
    resp = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    conversation_id = resp.get_json()["conversation_id"]

    db_session = app.extensions["db_session_factory"]()
    try:
        messages = conversation_repository.list_messages(db_session, conversation_id)
    finally:
        db_session.close()

    assert len(messages) == 2
    assert messages[0].sender_type == "customer"
    assert messages[0].content == "I want a kitchen remodel"
    assert messages[1].sender_type == "bot"
    assert "kitchen" in messages[1].content.lower()


def test_multi_turn_conversation_accumulates_transcript(app, client):
    r1 = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    conversation_id = r1.get_json()["conversation_id"]
    client.post(
        "/api/chat/message",
        json={"message": "How much will it cost?", "conversation_id": conversation_id, "session_id": "s1"},
    )

    db_session = app.extensions["db_session_factory"]()
    try:
        messages = conversation_repository.list_messages(db_session, conversation_id)
    finally:
        db_session.close()

    assert len(messages) == 4
