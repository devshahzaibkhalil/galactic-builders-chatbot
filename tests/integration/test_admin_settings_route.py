import pytest

from app import create_app
from app.constants.roles import AGENT, ADMIN
from app.services.authentication_service import create_admin_user


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    return {"X-CSRFToken": client.get("/admin/csrf-token").get_json()["csrf_token"]}


def _login_as(client, app, *, username, role):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(
        session, email=f"{username}@example.com", username=username, raw_password="Str0ng!Passw0rd", role=role
    )
    session.commit()
    session.close()
    client.post(
        "/admin/login", json={"username": username, "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )


def test_get_settings_returns_defaults(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.get("/admin/settings")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["primary_color"] == "#0d2238"
    assert body["accent_color"] == "#d2a33b"


def test_admin_can_update_theme(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings",
        json={"primary_color": "#112233", "accent_color": "#aabbcc"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.get_json()["primary_color"] == "#112233"


def test_agent_cannot_update_theme(client, app):
    _login_as(client, app, username="agent1", role=AGENT)
    resp = client.put(
        "/admin/settings",
        json={"primary_color": "#112233", "accent_color": "#aabbcc"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 403


def test_agent_can_still_view_theme(client, app):
    _login_as(client, app, username="agent1", role=AGENT)
    resp = client.get("/admin/settings")
    assert resp.status_code == 200


def test_invalid_color_rejected_via_api(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings", json={"primary_color": "purple", "accent_color": "#aabbcc"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 422


def test_settings_page_requires_login(client):
    resp = client.get("/admin/dashboard/settings")
    assert resp.status_code in (302, 401)


def test_settings_page_renders_when_logged_in(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.get("/admin/dashboard/settings")
    assert resp.status_code == 200
    assert b"Appearance" in resp.data
