from datetime import timedelta

import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.jobs.email_jobs import MAX_ATTEMPTS, RETRY_DELAYS, attempt_notification, next_retry_delay
from app.models.email_notification import EmailNotification, NotificationStatus
from app.models.lead import InterestResponse, Lead, LeadStatus
from app.services.email_service import (
    build_admin_subject,
    render_admin_notification,
    render_customer_confirmation,
    send_admin_notification,
    send_customer_confirmation,
)


def _make_lead(**overrides) -> Lead:
    defaults = dict(
        service_key="roof_repair",
        project_description="Leak near chimney.",
        city="South Bend",
        full_name="Jordan Smith",
        email="jordan@example.com",
        phone="(574) 555-0100",
        safety_flag=False,
        interest_response=InterestResponse.YES,
        status=LeadStatus.NEW,
        photo_count=0,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_subject_line_excludes_pii():
    lead = _make_lead(street_address="123 Main St", email="jordan@example.com", phone="(574) 555-0100")
    subject = build_admin_subject(lead)
    assert "123 Main St" not in subject
    assert "jordan@example.com" not in subject
    assert "555-0100" not in subject
    assert "Roof Repair" in subject
    assert "South Bend" in subject


def test_safety_flagged_lead_uses_priority_subject():
    lead = _make_lead(safety_flag=True)
    subject = build_admin_subject(lead)
    assert subject.startswith("Priority Project Request")


def test_admin_template_renders_all_required_fields():
    lead = _make_lead(street_address="123 Main St")
    body = render_admin_notification(lead, dashboard_url="https://admin.example.com/leads/abc")
    assert "roof_repair" in body
    assert "South Bend" in body
    assert "https://admin.example.com/leads/abc" in body
    assert "Jordan Smith" in body


def test_customer_template_states_not_a_final_quotation():
    lead = _make_lead()
    body = render_customer_confirmation(lead)
    assert "not a final quotation" in body.lower()
    assert "confirmed appointment" in body.lower()


def test_send_admin_notification_calls_transport_once():
    lead = _make_lead()
    calls = []

    def fake_transport(*, to, subject, body):
        calls.append((to, subject))

    send_admin_notification(lead, recipient="ops@example.com", dashboard_url="https://x", transport=fake_transport)
    assert len(calls) == 1
    assert calls[0][0] == "ops@example.com"


def test_send_customer_confirmation_skipped_without_email():
    lead = _make_lead(email=None)
    calls = []
    send_customer_confirmation(lead, transport=lambda **kw: calls.append(kw))
    assert calls == []


# -- retry policy --

def test_retry_delays_match_spec():
    assert RETRY_DELAYS[0] == timedelta(seconds=0)
    assert RETRY_DELAYS[1] == timedelta(minutes=2)
    assert RETRY_DELAYS[2] == timedelta(minutes=10)
    assert RETRY_DELAYS[3] == timedelta(minutes=30)
    assert MAX_ATTEMPTS == 4


def test_next_retry_delay_exhausted_after_max_attempts():
    assert next_retry_delay(MAX_ATTEMPTS) is None
    assert next_retry_delay(0) == timedelta(seconds=0)


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_successful_send_marks_sent(session):
    lead = _make_lead()
    session.add(lead)
    session.flush()
    notification = EmailNotification(lead_id=lead.id, notification_type="admin_lead")
    session.add(notification)
    session.flush()

    status = attempt_notification(session, notification, send=lambda n: None)
    assert status == NotificationStatus.SENT
    assert notification.attempt_count == 1


def test_failed_send_retries_until_max_then_fails(session):
    lead = _make_lead()
    session.add(lead)
    session.flush()
    notification = EmailNotification(lead_id=lead.id, notification_type="admin_lead")
    session.add(notification)
    session.flush()

    def always_fail(n):
        raise RuntimeError("SMTP unavailable")

    for expected_attempt in range(1, MAX_ATTEMPTS + 1):
        status = attempt_notification(session, notification, send=always_fail)
        assert notification.attempt_count == expected_attempt
        if expected_attempt < MAX_ATTEMPTS:
            assert status == NotificationStatus.RETRYING
        else:
            assert status == NotificationStatus.FAILED


def test_lead_untouched_by_email_failure(session):
    lead = _make_lead()
    session.add(lead)
    session.flush()
    notification = EmailNotification(lead_id=lead.id, notification_type="admin_lead")
    session.add(notification)
    session.flush()

    def always_fail(n):
        raise RuntimeError("fail")

    attempt_notification(session, notification, send=always_fail)
    assert lead.status == LeadStatus.NEW  # unchanged despite email failure
