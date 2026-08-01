import pytest
from sqlalchemy import text

from app import create_app

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


def test_lead_submitted_via_api_is_encrypted_at_rest(app, client):
    resp = client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    assert resp.status_code == 201

    db_session = app.extensions["db_session_factory"]()
    try:
        raw = db_session.execute(text("SELECT email_ciphertext FROM leads LIMIT 1")).scalar_one()
    finally:
        db_session.close()

    assert "jordan@example.com" not in raw
    assert "jordan" not in raw


def test_admin_leads_list_still_shows_correct_data_despite_encryption(app, client):
    from app.constants.roles import ADMIN
    from app.services.authentication_service import create_admin_user

    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)

    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    create_admin_user(
        session, email="admin@example.com", username="admin1", raw_password="Str0ng!Passw0rd", role=ADMIN
    )
    session.commit()
    session.close()

    token = client.get("/admin/csrf-token").get_json()["csrf_token"]
    client.post(
        "/admin/login",
        json={"username": "admin1", "password": "Str0ng!Passw0rd"},
        headers={"X-CSRFToken": token},
    )

    resp = client.get("/admin/leads")
    leads = resp.get_json()["leads"]
    assert len(leads) == 1
    assert leads[0]["service_key"] == "kitchen_remodeling"


def test_duplicate_detection_still_works_with_encrypted_email(client):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    second = client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    assert second.status_code == 422
    assert second.get_json()["fields"]["spam"] == "duplicate_submission"
