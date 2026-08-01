import pytest

from app import create_app
from app.constants.roles import ADMIN
from app.services.authentication_service import create_admin_user


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    return {"X-CSRFToken": client.get("/admin/csrf-token").get_json()["csrf_token"]}


def _login(client, app):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(
        session, email="admin@example.com", username="admin1", raw_password="Str0ng!Passw0rd", role=ADMIN
    )
    session.commit()
    session.close()
    client.post(
        "/admin/login", json={"username": "admin1", "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )


def test_login_page_renders_without_auth(client):
    resp = client.get("/admin/dashboard/login")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")
    assert b"Sign in" in resp.data


def test_leads_page_requires_login(client):
    resp = client.get("/admin/dashboard/leads")
    assert resp.status_code in (302, 401)


def test_leads_page_redirects_unauthenticated_to_login(client):
    resp = client.get("/admin/dashboard/leads", follow_redirects=False)
    if resp.status_code == 302:
        assert "/admin/dashboard/login" in resp.headers["Location"]


def test_leads_page_renders_once_logged_in(client, app):
    _login(client, app)
    resp = client.get("/admin/dashboard/leads")
    assert resp.status_code == 200
    assert b"Leads" in resp.data


def test_conversation_detail_page_requires_login(client):
    resp = client.get("/admin/dashboard/conversations/some-id")
    assert resp.status_code in (302, 401)


def test_conversation_detail_page_renders_once_logged_in(client, app):
    _login(client, app)
    resp = client.get("/admin/dashboard/conversations/some-id")
    assert resp.status_code == 200
    assert b"some-id" in resp.data


def test_static_admin_css_is_served(client):
    resp = client.get("/static/admin/css/admin.css")
    assert resp.status_code == 200
    assert b"--navy-900" in resp.data


def test_static_admin_js_is_served(client):
    resp = client.get("/static/admin/js/admin.js")
    assert resp.status_code == 200
    assert b"AdminAPI" in resp.data
