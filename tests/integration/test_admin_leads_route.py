import pytest

from app import create_app
from app.constants.roles import ADMIN, AGENT
from app.services.authentication_service import create_admin_user

VALID_LEAD_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "project_description": "Replace cabinets and countertops.",
    "full_name": "Jordan Smith",
    "email": "jordan@example.com",
    "phone": "574-555-0100",
    "interest_response": "yes",
    "contact_consent_given": True,
}


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    token = client.get("/admin/csrf-token").get_json()["csrf_token"]
    return {"X-CSRFToken": token}


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


def test_admin_can_list_leads_with_priority_and_readiness(client, app):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    _login_as(client, app, username="admin1", role=ADMIN)

    resp = client.get("/admin/leads")
    assert resp.status_code == 200
    leads = resp.get_json()["leads"]
    assert len(leads) == 1
    assert leads[0]["service_key"] == "kitchen_remodeling"
    assert "priority_label" in leads[0]
    assert "readiness_percent" in leads[0]
    assert leads[0]["public_reference"].startswith("GB-")


def test_agent_cannot_list_all_leads(client, app):
    _login_as(client, app, username="agent1", role=AGENT)
    resp = client.get("/admin/leads")
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_leads(client):
    resp = client.get("/admin/leads")
    assert resp.status_code in (401, 302)
