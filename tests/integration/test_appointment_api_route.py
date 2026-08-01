import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_create_callback_via_api(client):
    resp = client.post("/api/appointments", json={"appointment_type": "callback", "phone": "574-555-0100"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["appointment_type"] == "callback"
    assert body["status"] == "requested"


def test_invalid_appointment_type_rejected(client):
    resp = client.post("/api/appointments", json={"appointment_type": "banana", "phone": "574-555-0100"})
    assert resp.status_code == 422


def test_appointment_api_exempt_from_csrf(client):
    # No CSRF token supplied — should still succeed since this is a public endpoint.
    resp = client.post("/api/appointments", json={"appointment_type": "consultation", "email": "a@b.com"})
    assert resp.status_code == 201
