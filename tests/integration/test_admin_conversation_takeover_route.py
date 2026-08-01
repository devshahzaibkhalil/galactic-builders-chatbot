import pytest

from app import create_app
from app.constants.roles import AGENT
from app.services.authentication_service import create_admin_user


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    token = client.get("/admin/csrf-token").get_json()["csrf_token"]
    return {"X-CSRFToken": token}


@pytest.fixture()
def logged_in_agent(app, client):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(
        session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT
    )
    session.commit()
    session.close()
    client.post(
        "/admin/login", json={"username": "agent1", "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )


def _start_conversation(client) -> str:
    resp = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    return resp.get_json()["conversation_id"]


def test_agent_can_take_over_conversation(client, logged_in_agent):
    conversation_id = _start_conversation(client)

    resp = client.post(f"/admin/conversations/{conversation_id}/takeover", headers=_csrf_headers(client))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["mode"] == "admin_active"
    assert body["human_takeover_active"] is True


def test_bot_stays_silent_after_takeover_over_real_http(client, logged_in_agent):
    conversation_id = _start_conversation(client)
    client.post(f"/admin/conversations/{conversation_id}/takeover", headers=_csrf_headers(client))

    resp = client.post(
        "/api/chat/message",
        json={"message": "What's my status?", "conversation_id": conversation_id, "session_id": "s1"},
    )
    body = resp.get_json()
    assert body["handled_by"] == "human_takeover"
    assert "Galactic Builders team" in body["response"]


def test_agent_can_send_message_and_return_to_bot(client, logged_in_agent):
    conversation_id = _start_conversation(client)
    headers = _csrf_headers(client)
    client.post(f"/admin/conversations/{conversation_id}/takeover", headers=headers)

    send_resp = client.post(
        f"/admin/conversations/{conversation_id}/messages", json={"message": "I'm here to help!"}, headers=headers
    )
    assert send_resp.status_code == 201

    return_resp = client.post(f"/admin/conversations/{conversation_id}/return-to-bot", headers=headers)
    assert return_resp.status_code == 200
    assert return_resp.get_json()["mode"] == "bot_active"

    # Transcript should show the admin's message.
    view_resp = client.get(f"/admin/conversations/{conversation_id}", headers=headers)
    transcript = view_resp.get_json()["transcript"]
    assert any(m["sender_type"] == "admin" and m["content"] == "I'm here to help!" for m in transcript)


def test_takeover_requires_login(client):
    conversation_id = "some-id"
    resp = client.post(f"/admin/conversations/{conversation_id}/takeover", headers=_csrf_headers(client))
    assert resp.status_code in (401, 302)


def test_takeover_of_nonexistent_conversation_returns_404(client, logged_in_agent):
    resp = client.post("/admin/conversations/does-not-exist/takeover", headers=_csrf_headers(client))
    assert resp.status_code == 404
