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
    create_admin_user(
        session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT
    )
    session.commit()
    session.close()


def _csrf_headers(client) -> dict:
    resp = client.get("/admin/csrf-token")
    token = resp.get_json()["csrf_token"]
    return {"X-CSRFToken": token}


def test_login_success_sets_session(client, seeded_user):
    resp = client.post(
        "/admin/login", json={"username": "agent1", "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["username"] == "agent1"
    assert body["role"] == "agent"

    me_resp = client.get("/admin/me")
    assert me_resp.status_code == 200
    assert me_resp.get_json()["username"] == "agent1"


def test_login_wrong_password_returns_401(client, seeded_user):
    resp = client.post(
        "/admin/login", json={"username": "agent1", "password": "wrong"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 401


def test_me_requires_login(client):
    resp = client.get("/admin/me")
    assert resp.status_code in (401, 302)  # flask-login default redirects unless configured for JSON 401


def test_logout_clears_session(client, seeded_user):
    client.post("/admin/login", json={"username": "agent1", "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client))
    # session.clear() during login rotates the session, invalidating the
    # pre-login CSRF token — fetch a fresh one, same as a real client would.
    logout_resp = client.post("/admin/logout", headers=_csrf_headers(client))
    assert logout_resp.status_code == 200

    me_resp = client.get("/admin/me")
    assert me_resp.status_code in (401, 302)
