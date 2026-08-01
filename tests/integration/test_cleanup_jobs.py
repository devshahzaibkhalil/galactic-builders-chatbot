from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.jobs.cleanup_jobs import (
    purge_expired_uploaded_files,
    purge_failed_upload_attempts,
    purge_old_email_notification_records,
    soft_delete_expired_leads,
)
from app.models.email_notification import EmailNotification, NotificationStatus
from app.models.lead import InterestResponse, Lead, LeadStatus
from app.models.uploaded_file import UploadedFile
from app.services.storage_service import StorageService


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def _make_lead(**overrides) -> Lead:
    defaults = dict(
        service_key="kitchen_remodeling",
        project_description="x",
        email="jordan@example.com",
        phone="574-555-0100",
        interest_response=InterestResponse.YES,
        status=LeadStatus.NEW,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_old_lead_soft_deleted(session):
    now = datetime.now(timezone.utc)
    old_lead = _make_lead()
    session.add(old_lead)
    session.commit()
    # Backdate created_at past the retention window.
    old_lead.created_at = now - timedelta(days=800)
    session.commit()

    recent_lead = _make_lead(email="recent@example.com")
    session.add(recent_lead)
    session.commit()

    count = soft_delete_expired_leads(session, retention_days=730, now=now)
    session.commit()

    assert count == 1
    assert old_lead.deleted_at is not None
    assert recent_lead.deleted_at is None


def test_already_deleted_lead_not_touched_twice(session):
    now = datetime.now(timezone.utc)
    lead = _make_lead()
    session.add(lead)
    session.commit()
    lead.created_at = now - timedelta(days=800)
    lead.deleted_at = now - timedelta(days=1)
    session.commit()

    count = soft_delete_expired_leads(session, retention_days=730, now=now)
    assert count == 0


def test_purge_expired_uploaded_files_deletes_from_storage_and_marks_record(session, tmp_path):
    storage = StorageService(tmp_path)
    storage_name = storage.generate_storage_name("png")
    storage.save(storage_name, b"fake-image-bytes")

    now = datetime.now(timezone.utc)
    record = UploadedFile(
        lead_id="lead-1",
        storage_name=storage_name,
        original_filename="photo.png",
        mime_type="image/png",
        size_bytes=16,
        expires_at=now - timedelta(days=1),
    )
    session.add(record)
    session.commit()

    purged = purge_expired_uploaded_files(session, storage, now=now)
    session.commit()

    assert purged == 1
    assert record.deleted_at is not None
    assert not (tmp_path / storage_name).exists()


def test_not_yet_expired_file_is_untouched(session, tmp_path):
    storage = StorageService(tmp_path)
    now = datetime.now(timezone.utc)
    record = UploadedFile(
        lead_id="lead-1",
        storage_name="still-valid.png",
        original_filename="photo.png",
        mime_type="image/png",
        size_bytes=16,
        expires_at=now + timedelta(days=30),
    )
    session.add(record)
    session.commit()

    purged = purge_expired_uploaded_files(session, storage, now=now)
    assert purged == 0
    assert record.deleted_at is None


def test_purge_old_terminal_notifications(session):
    now = datetime.now(timezone.utc)
    lead = _make_lead()
    session.add(lead)
    session.commit()

    old_sent = EmailNotification(
        lead_id=lead.id, notification_type="admin_lead", status=NotificationStatus.SENT
    )
    session.add(old_sent)
    session.commit()
    old_sent.created_at = now - timedelta(days=100)
    session.commit()

    recent_sent = EmailNotification(
        lead_id=lead.id, notification_type="admin_lead", status=NotificationStatus.SENT
    )
    session.add(recent_sent)
    session.commit()

    old_pending = EmailNotification(
        lead_id=lead.id, notification_type="admin_lead", status=NotificationStatus.PENDING
    )
    session.add(old_pending)
    session.commit()
    old_pending.created_at = now - timedelta(days=100)
    session.commit()

    purged = purge_old_email_notification_records(session, retention_days=30, now=now)
    session.commit()

    assert purged == 1  # only the old SENT one
    remaining_ids = {n.id for n in session.query(EmailNotification).all()}
    assert recent_sent.id in remaining_ids
    assert old_pending.id in remaining_ids  # never purged regardless of age


def test_purge_failed_upload_attempts(session):
    now = datetime.now(timezone.utc)
    old = UploadedFile(
        lead_id="lead-1", storage_name="a.png", original_filename="a.png",
        mime_type="image/png", size_bytes=1,
    )
    session.add(old)
    session.commit()
    old.created_at = now - timedelta(days=10)
    session.commit()

    count = purge_failed_upload_attempts(session, retention_days=7, now=now)
    assert count == 1
    assert old.deleted_at is not None
