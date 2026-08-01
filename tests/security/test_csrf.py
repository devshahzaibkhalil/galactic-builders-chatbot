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


@pytest.fixture()
def seeded_user(app):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT)
    session.commit()
    session.close()


def test_login_without_csrf_token_is_rejected(client, seeded_user):
    resp = client.post("/admin/login", json={"username": "agent1", "password": "Str0ng!Passw0rd"})
    assert resp.status_code == 400


def test_login_with_valid_csrf_token_succeeds(client, seeded_user):
    token = client.get("/admin/csrf-token").get_json()["csrf_token"]
    resp = client.post(
        "/admin/login",
        json={"username": "agent1", "password": "Str0ng!Passw0rd"},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 200


def test_login_with_garbage_csrf_token_is_rejected(client, seeded_user):
    resp = client.post(
        "/admin/login",
        json={"username": "agent1", "password": "Str0ng!Passw0rd"},
        headers={"X-CSRFToken": "not-a-real-token"},
    )
    assert resp.status_code == 400


def test_public_chat_api_is_exempt_from_csrf(client):
    # Customer-facing JSON API carries no ambient session credential, so it
    # must keep working without any CSRF token.
    resp = client.post("/api/chat/message", json={"message": "hello", "session_id": "s1"})
    assert resp.status_code == 200


def test_public_lead_api_is_exempt_from_csrf(client):
    resp = client.post("/api/leads", json={})
    # Rejected for validation reasons, not CSRF (would be 400 from CSRFProtect otherwise).
    assert resp.status_code == 422
