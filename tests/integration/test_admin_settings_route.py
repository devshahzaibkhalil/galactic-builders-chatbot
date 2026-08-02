import pytest

from app import create_app
from app.constants.roles import AGENT, ADMIN, SUPERADMIN
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


# ---------------------------------------------------------------------------
# My account
# ---------------------------------------------------------------------------

def test_get_account_returns_current_user(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.get("/admin/settings/account")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["username"] == "admin1"
    assert body["email"] == "admin1@example.com"


def test_update_account_changes_email_and_username(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings/account",
        json={
            "email": "newmail@example.com",
            "username": "admin1renamed",
            "current_password": "Str0ng!Passw0rd",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["email"] == "newmail@example.com"
    assert body["username"] == "admin1renamed"


def test_update_account_rejects_wrong_current_password(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings/account",
        json={"email": "newmail@example.com", "username": "admin1", "current_password": "wrong-password"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401


def test_update_account_rejects_duplicate_email(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    _login_as(client, app, username="admin2", role=ADMIN)
    resp = client.put(
        "/admin/settings/account",
        json={
            "email": "admin1@example.com",
            "username": "admin2",
            "current_password": "Str0ng!Passw0rd",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 409


def test_update_password_success_and_relogin(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings/password",
        json={"current_password": "Str0ng!Passw0rd", "new_password": "N3w!Str0ngerPassw0rd"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200

    client.post("/admin/logout", headers=_csrf_headers(client))
    login_resp = client.post(
        "/admin/login",
        json={"username": "admin1", "password": "N3w!Str0ngerPassw0rd"},
        headers=_csrf_headers(client),
    )
    assert login_resp.status_code == 200


def test_update_password_rejects_wrong_current_password(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings/password",
        json={"current_password": "wrong-password", "new_password": "N3w!Str0ngerPassw0rd"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401


def test_update_password_rejects_weak_password(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.put(
        "/admin/settings/password",
        json={"current_password": "Str0ng!Passw0rd", "new_password": "weak"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Lead notification email
# ---------------------------------------------------------------------------

def test_admin_cannot_view_notification_settings(client, app):
    _login_as(client, app, username="admin1", role=ADMIN)
    resp = client.get("/admin/settings/notifications")
    assert resp.status_code == 403


def test_superadmin_can_update_lead_notification_email(client, app):
    _login_as(client, app, username="super1", role=SUPERADMIN)
    resp = client.put(
        "/admin/settings/notifications",
        json={"lead_notification_email": "leads@example.com"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["lead_notification_email"] == "leads@example.com"
    assert body["source"] == "dashboard"

    get_resp = client.get("/admin/settings/notifications")
    assert get_resp.get_json()["lead_notification_email"] == "leads@example.com"


def test_superadmin_can_clear_lead_notification_email_override(client, app):
    _login_as(client, app, username="super1", role=SUPERADMIN)
    client.put(
        "/admin/settings/notifications",
        json={"lead_notification_email": "leads@example.com"},
        headers=_csrf_headers(client),
    )
    resp = client.put(
        "/admin/settings/notifications",
        json={"lead_notification_email": ""},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.get_json()["source"] == "env"


def test_superadmin_rejects_invalid_lead_notification_email(client, app):
    _login_as(client, app, username="super1", role=SUPERADMIN)
    resp = client.put(
        "/admin/settings/notifications",
        json={"lead_notification_email": "not-an-email"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 422
