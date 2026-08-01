import pytest
from sqlalchemy.orm import Session

from app.extensions import build_engine, build_session_factory, create_all
from app.models.email_notification import EmailNotification
from app.models.lead import Lead, LeadStatus
from app.services.lead_service import (
    InterestNotConfirmedError,
    LeadValidationError,
    submit_lead,
)


@pytest.fixture()
def session() -> Session:
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    factory = build_session_factory(engine)
    s = factory()
    yield s
    s.close()


VALID_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "project_description": "Replace cabinets and countertops.",
    "city": "South Bend",
    "state": "IN",
    "zip_code": "46601",
    "full_name": "Jordan Smith",
    "email": "jordan@example.com",
    "phone": "574-555-0100",
    "preferred_contact_method": "email",
    "interest_response": "yes",
    "contact_consent_given": True,
}


def test_lead_saved_before_email_is_queued(session):
    call_order = []

    def fake_queue_email(lead_id, notification_type):
        # By the time this runs, the lead must already be committed.
        found = session.get(Lead, lead_id)
        assert found is not None
        assert found.status == LeadStatus.NEW
        call_order.append(notification_type)

    lead = submit_lead(session, VALID_PAYLOAD, queue_email=fake_queue_email)

    assert lead.id is not None
    assert lead.public_reference.startswith("GB-")
    assert "admin_lead" in call_order
    assert "customer_confirmation" in call_order

    notifications = session.query(EmailNotification).filter_by(lead_id=lead.id).all()
    assert len(notifications) == 2


def test_email_never_queued_if_validation_fails(session):
    called = []

    def fake_queue_email(lead_id, notification_type):
        called.append(notification_type)

    bad_payload = dict(VALID_PAYLOAD)
    bad_payload["email"] = "not-an-email"

    with pytest.raises(LeadValidationError):
        submit_lead(session, bad_payload, queue_email=fake_queue_email)

    assert called == []
    assert session.query(Lead).count() == 0


def test_transaction_rolls_back_on_missing_consent(session):
    called = []
    bad_payload = dict(VALID_PAYLOAD)
    bad_payload["contact_consent_given"] = False

    with pytest.raises(LeadValidationError):
        submit_lead(session, bad_payload, queue_email=lambda *a: called.append(a))

    assert called == []
    assert session.query(Lead).count() == 0


def test_cannot_submit_before_interest_confirmed_yes(session):
    called = []
    payload = dict(VALID_PAYLOAD)
    payload["interest_response"] = "no"

    with pytest.raises((LeadValidationError, InterestNotConfirmedError)):
        submit_lead(session, payload, queue_email=lambda *a: called.append(a))

    assert called == []
    assert session.query(Lead).count() == 0


def test_second_submission_within_window_is_flagged_as_duplicate(session):
    submit_lead(session, VALID_PAYLOAD, queue_email=lambda *a: None)

    with pytest.raises(LeadValidationError) as exc_info:
        submit_lead(session, VALID_PAYLOAD, queue_email=lambda *a: None)

    assert exc_info.value.errors.get("spam") == "duplicate_submission"
    assert session.query(Lead).count() == 1


def test_submission_for_different_service_is_not_flagged_as_duplicate(session):
    submit_lead(session, VALID_PAYLOAD, queue_email=lambda *a: None)

    other_payload = dict(VALID_PAYLOAD)
    other_payload["service_key"] = "roof_repair"
    submit_lead(session, other_payload, queue_email=lambda *a: None)

    assert session.query(Lead).count() == 2
