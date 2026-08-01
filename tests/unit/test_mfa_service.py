import pytest

from app.constants.roles import AGENT, SUPERADMIN
from app.extensions import build_engine, build_session_factory, create_all
from app.services import mfa_service
from app.services.authentication_service import (
    begin_mfa_enrollment,
    confirm_mfa_enrollment,
    create_admin_user,
    requires_mfa,
    verify_mfa_login_code,
)


def test_generated_code_verifies_against_own_secret():
    secret = mfa_service.generate_secret()
    code = mfa_service.current_code(secret)
    assert mfa_service.verify_code(secret, code)


def test_wrong_code_rejected():
    secret = mfa_service.generate_secret()
    assert not mfa_service.verify_code(secret, "000000")


def test_non_numeric_code_rejected():
    secret = mfa_service.generate_secret()
    assert not mfa_service.verify_code(secret, "not-a-code")


def test_provisioning_uri_includes_issuer_and_account():
    secret = mfa_service.generate_secret()
    uri = mfa_service.get_provisioning_uri(secret, "admin@example.com")
    assert uri.startswith("otpauth://totp/")
    assert "admin%40example.com" in uri  # URI-encoded @
    assert "Galactic" in uri


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_agent_does_not_require_mfa_by_default(session):
    user = create_admin_user(
        session, email="a@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT
    )
    assert not requires_mfa(user)


def test_superadmin_without_enrollment_does_not_require_mfa(session):
    user = create_admin_user(
        session, email="s@example.com", username="super1", raw_password="Str0ng!Passw0rd", role=SUPERADMIN
    )
    assert not requires_mfa(user)


def test_enrollment_flow_enables_mfa_only_after_valid_code(session):
    user = create_admin_user(
        session, email="s@example.com", username="super1", raw_password="Str0ng!Passw0rd", role=SUPERADMIN
    )
    secret, uri = begin_mfa_enrollment(user)
    assert user.mfa_enabled is False  # not enabled until confirmed

    ok = confirm_mfa_enrollment(user, secret=secret, code="000000")
    assert not ok
    assert user.mfa_enabled is False

    valid_code = mfa_service.current_code(secret)
    ok = confirm_mfa_enrollment(user, secret=secret, code=valid_code)
    assert ok
    assert user.mfa_enabled is True
    assert requires_mfa(user)


def test_verify_mfa_login_code_uses_stored_secret(session):
    user = create_admin_user(
        session, email="s@example.com", username="super1", raw_password="Str0ng!Passw0rd", role=SUPERADMIN
    )
    secret, _ = begin_mfa_enrollment(user)
    confirm_mfa_enrollment(user, secret=secret, code=mfa_service.current_code(secret))

    assert verify_mfa_login_code(user, mfa_service.current_code(secret))
    assert not verify_mfa_login_code(user, "111111")
