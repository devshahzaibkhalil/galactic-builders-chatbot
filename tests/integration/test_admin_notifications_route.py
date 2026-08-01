import pytest

from app import create_app
from app.constants.roles import ADMIN, AGENT
from app.services.authentication_service import create_admin_user

VALID_LEAD_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "project_description": "Replace cabinets and countertops.",
    "city": "South Bend",
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
    return {"X-CSRFToken": client.get("/admin/csrf-token").get_json()["csrf_token"]}


def _login_as(client, app, *, username, role):
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    user = create_admin_user(
        session, email=f"{username}@example.com", username=username, raw_password="Str0ng!Passw0rd", role=role
    )
    session.commit()
    user_id = user.id
    session.close()
    client.post(
        "/admin/login", json={"username": username, "password": "Str0ng!Passw0rd"}, headers=_csrf_headers(client)
    )
    return user_id


def test_new_lead_creates_broadcast_notification_visible_to_admin(client, app):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    _login_as(client, app, username="admin1", role=ADMIN)

    resp = client.get("/admin/notifications")
    assert resp.status_code == 200
    notifications = resp.get_json()["notifications"]
    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "new_lead"


def test_mark_notification_read_removes_it(client, app):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    _login_as(client, app, username="admin1", role=ADMIN)
    headers = _csrf_headers(client)

    notification_id = client.get("/admin/notifications").get_json()["notifications"][0]["id"]
    read_resp = client.post(f"/admin/notifications/{notification_id}/read", headers=headers)
    assert read_resp.status_code == 200

    assert client.get("/admin/notifications").get_json()["notifications"] == []


def test_assign_lead_creates_targeted_notification_for_assignee(client, app):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)

    admin_id = _login_as(client, app, username="admin1", role=ADMIN)

    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    from app.models.lead import Lead
    lead = session.query(Lead).first()
    lead_id = lead.id
    session.close()

    headers = _csrf_headers(client)
    resp = client.post(f"/admin/leads/{lead_id}/assign", json={"admin_id": admin_id}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["assigned_admin_id"] == admin_id

    notifications = client.get("/admin/notifications").get_json()["notifications"]
    assert any(n["notification_type"] == "lead_assigned" for n in notifications)


def test_agent_cannot_assign_leads(client, app):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    _login_as(client, app, username="agent1", role=AGENT)

    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    from app.models.lead import Lead
    lead_id = session.query(Lead).first().id
    session.close()

    resp = client.post(
        f"/admin/leads/{lead_id}/assign", json={"admin_id": "someone"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 403
