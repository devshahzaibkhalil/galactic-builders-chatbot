"""Regression tests for lead notification recipient resolution.

The admin_lead email used to read LEAD_NOTIFICATION_EMAIL straight from the
environment, bypassing the dashboard override that Settings -> Lead
notifications writes to the database. A deployment configured only through
the dashboard therefore raised "LEAD_NOTIFICATION_EMAIL is not set" on every
lead, and email_jobs swallowed the error without logging it.
"""
from __future__ import annotations

import logging

import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.jobs.email_jobs import MAX_ATTEMPTS, attempt_notification
from app.models.email_notification import EmailNotification, NotificationStatus
from app.services import dashboard_settings_service


@pytest.fixture()
def db_session():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401
    create_all(engine)
    session = build_session_factory(engine)()
    yield session
    session.close()


def test_dashboard_override_is_used_when_env_var_is_absent(db_session, monkeypatch):
    monkeypatch.delenv("LEAD_NOTIFICATION_EMAIL", raising=False)
    dashboard_settings_service.update_lead_notification_email(db_session, "ops@example.com")
    db_session.flush()

    assert dashboard_settings_service.get_lead_notification_email(db_session) == "ops@example.com"


def test_env_var_is_the_fallback_when_no_override_saved(db_session, monkeypatch):
    monkeypatch.setenv("LEAD_NOTIFICATION_EMAIL", "fallback@example.com")
    assert dashboard_settings_service.get_lead_notification_email(db_session) == "fallback@example.com"


def test_dashboard_override_wins_over_env_var(db_session, monkeypatch):
    monkeypatch.setenv("LEAD_NOTIFICATION_EMAIL", "fallback@example.com")
    dashboard_settings_service.update_lead_notification_email(db_session, "ops@example.com")
    db_session.flush()

    assert dashboard_settings_service.get_lead_notification_email(db_session) == "ops@example.com"


def test_failed_attempt_is_logged_not_swallowed(db_session, caplog):
    """A send failure must leave a traceback in the logs; previously the
    reason vanished and only a RETRYING status remained."""
    # attempt_count's default is applied on INSERT, so set it explicitly on
    # this transient row.
    notification = EmailNotification(
        lead_id="lead-1", notification_type="admin_lead", attempt_count=0
    )

    def boom(_notification):
        raise RuntimeError("no recipient configured")

    with caplog.at_level(logging.ERROR, logger="galactic.email_jobs"):
        status = attempt_notification(db_session, notification, boom)

    assert status is NotificationStatus.RETRYING
    assert "no recipient configured" in caplog.text


def test_status_is_failed_once_retries_are_exhausted(db_session):
    notification = EmailNotification(lead_id="lead-1", notification_type="admin_lead")
    notification.attempt_count = MAX_ATTEMPTS - 1

    def boom(_notification):
        raise RuntimeError("still broken")

    assert attempt_notification(db_session, notification, boom) is NotificationStatus.FAILED
