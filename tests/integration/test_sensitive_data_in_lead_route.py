import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_lead_with_ssn_in_description_rejected(client):
    payload = {
        "service_key": "kitchen_remodeling",
        "project_description": "Here's my SSN 123-45-6789 for reference.",
        "email": "jordan@example.com",
        "phone": "574-555-0100",
        "interest_response": "yes",
        "contact_consent_given": True,
    }
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 422
    assert resp.get_json()["fields"]["project_description"]


def test_lead_with_normal_description_accepted(client):
    payload = {
        "service_key": "kitchen_remodeling",
        "project_description": "Replace cabinets and countertops.",
        "email": "jordan2@example.com",
        "phone": "574-555-0100",
        "interest_response": "yes",
        "contact_consent_given": True,
    }
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 201
