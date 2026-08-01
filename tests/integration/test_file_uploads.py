import io

import pytest

from app import create_app

PNG_BYTES = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"0" * 100
PHP_PAYLOAD = b'<?php system($_GET["c"]); ?>' + b"0" * 100

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
def app(tmp_path):
    flask_app = create_app("testing")
    flask_app.extensions["storage_service"].root = tmp_path
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _lead_db_id(app):
    from app.models.lead import Lead
    session = app.extensions["db_session_factory"]()
    lead = session.query(Lead).first()
    session.close()
    return lead.id


def test_valid_photo_upload_succeeds(app, client):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    lead_db_id = _lead_db_id(app)

    data = {"file": (io.BytesIO(PNG_BYTES), "kitchen.png")}
    resp = client.post(f"/api/leads/{lead_db_id}/uploads", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["mime_type"] == "image/png"
    assert body["original_filename"] == "kitchen.png"


def test_malicious_file_disguised_as_image_is_rejected(app, client):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    lead_db_id = _lead_db_id(app)

    data = {"file": (io.BytesIO(PHP_PAYLOAD), "photo.jpg")}
    resp = client.post(f"/api/leads/{lead_db_id}/uploads", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422


def test_missing_file_field_returns_400(app, client):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    lead_db_id = _lead_db_id(app)
    resp = client.post(f"/api/leads/{lead_db_id}/uploads", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_uploaded_file_stored_under_random_name_not_original(app, client, tmp_path):
    client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    lead_db_id = _lead_db_id(app)

    data = {"file": (io.BytesIO(PNG_BYTES), "my_house_address_123_main_st.png")}
    client.post(f"/api/leads/{lead_db_id}/uploads", data=data, content_type="multipart/form-data")

    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert "my_house_address" not in stored_files[0].name
