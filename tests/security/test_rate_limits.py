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


def _csrf_headers(client) -> dict:
    token = client.get("/admin/csrf-token").get_json()["csrf_token"]
    return {"X-CSRFToken": token}


def test_login_endpoint_rate_limited_after_threshold(client, seeded_user):
    headers = _csrf_headers(client)
    statuses = []
    for _ in range(15):
        resp = client.post(
            "/admin/login", json={"username": "agent1", "password": "wrong"}, headers=headers
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Expected a 429 among {statuses}"


def test_health_endpoint_not_subject_to_login_rate_limit(client):
    for _ in range(15):
        resp = client.get("/health")
        assert resp.status_code == 200
