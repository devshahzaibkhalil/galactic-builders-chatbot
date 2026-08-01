import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _start_conversation(client) -> str:
    resp = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    return resp.get_json()["conversation_id"]


def test_create_bookmark_requires_existing_conversation(client):
    resp = client.post("/api/chat/bookmark", json={"conversation_id": "does-not-exist", "contact_value": "a@b.com"})
    assert resp.status_code == 404


def test_create_and_resume_bookmark_end_to_end(client):
    conversation_id = _start_conversation(client)

    create_resp = client.post(
        "/api/chat/bookmark", json={"conversation_id": conversation_id, "contact_value": "jordan@example.com"}
    )
    assert create_resp.status_code == 200
    token = create_resp.get_json()["bookmark_token"]
    assert conversation_id not in token  # token isn't just the raw id

    resume_resp = client.post(
        "/api/chat/resume", json={"bookmark_token": token, "contact_value": "jordan@example.com"}
    )
    assert resume_resp.status_code == 200
    assert resume_resp.get_json()["conversation_id"] == conversation_id


def test_resume_with_wrong_identity_rejected(client):
    conversation_id = _start_conversation(client)
    create_resp = client.post(
        "/api/chat/bookmark", json={"conversation_id": conversation_id, "contact_value": "jordan@example.com"}
    )
    token = create_resp.get_json()["bookmark_token"]

    resume_resp = client.post(
        "/api/chat/resume", json={"bookmark_token": token, "contact_value": "wrong@example.com"}
    )
    assert resume_resp.status_code == 401


def test_resume_with_garbage_token_rejected(client):
    resp = client.post("/api/chat/resume", json={"bookmark_token": "garbage", "contact_value": "a@b.com"})
    assert resp.status_code == 401


def test_resume_missing_fields_returns_400(client):
    resp = client.post("/api/chat/resume", json={})
    assert resp.status_code == 400
