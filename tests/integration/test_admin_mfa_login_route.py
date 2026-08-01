import pytest

from app import create_app
from app.constants.roles import AGENT, SUPERADMIN
from app.services import mfa_service
from app.services.authentication_service import (
    begin_mfa_enrollment,
    confirm_mfa_enrollment,
    create_admin_user,
)


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
def mfa_superadmin(app):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    user = create_admin_user(
        session, email="super@example.com", username="super1", raw_password="Str0ng!Passw0rd", role=SUPERADMIN
    )
    secret, _ = begin_mfa_enrollment(user)
    confirm_mfa_enrollment(user, secret=secret, code=mfa_service.current_code(secret))
    session.commit()
    return {"username": "super1", "secret": secret}


@pytest.fixture()
def plain_agent(app):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(
        session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT
    )
    session.commit()


def test_agent_login_completes_in_one_step(client, plain_agent):
    resp = client.post(
        "/admin/login", json={"username": "agent1", "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 200
    assert "mfa_required" not in resp.get_json()

    me = client.get("/admin/me")
    assert me.status_code == 200


def test_superadmin_login_requires_mfa_step(client, mfa_superadmin):
    resp = client.post(
        "/admin/login",
        json={"username": "super1", "password": "Str0ng!Passw0rd"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["mfa_required"] is True
    assert "mfa_pending_token" in body

    # Not logged in yet.
    me = client.get("/admin/me")
    assert me.status_code in (401, 302)


def test_superadmin_completes_login_with_valid_totp_code(client, mfa_superadmin):
    headers = _csrf_headers(client)
    step1 = client.post(
        "/admin/login", json={"username": "super1", "password": "Str0ng!Passw0rd"}, headers=headers
    )
    pending_token = step1.get_json()["mfa_pending_token"]
    code = mfa_service.current_code(mfa_superadmin["secret"])

    step2 = client.post(
        "/admin/login/mfa", json={"mfa_pending_token": pending_token, "code": code}, headers=headers
    )
    assert step2.status_code == 200
    assert step2.get_json()["username"] == "super1"

    me = client.get("/admin/me")
    assert me.status_code == 200


def test_wrong_totp_code_rejected(client, mfa_superadmin):
    headers = _csrf_headers(client)
    step1 = client.post(
        "/admin/login", json={"username": "super1", "password": "Str0ng!Passw0rd"}, headers=headers
    )
    pending_token = step1.get_json()["mfa_pending_token"]

    step2 = client.post(
        "/admin/login/mfa", json={"mfa_pending_token": pending_token, "code": "000000"}, headers=headers
    )
    assert step2.status_code == 401

    me = client.get("/admin/me")
    assert me.status_code in (401, 302)


def test_mfa_step_rejects_garbage_pending_token(client, mfa_superadmin):
    headers = _csrf_headers(client)
    resp = client.post(
        "/admin/login/mfa", json={"mfa_pending_token": "garbage", "code": "123456"}, headers=headers
    )
    assert resp.status_code == 401
