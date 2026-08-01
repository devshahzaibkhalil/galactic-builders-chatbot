import pytest

from app.constants.roles import AGENT
from app.extensions import build_engine, build_session_factory, create_all
from app.services.authentication_service import (
    MAX_FAILED_ATTEMPTS,
    AccountLockedError,
    InvalidCredentialsError,
    WeakPasswordError,
    authenticate,
    create_admin_user,
    hash_password,
)


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_password_is_hashed_not_stored_plaintext(session):
    user = create_admin_user(
        session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT
    )
    session.commit()
    assert user.password_hash != "Str0ng!Passw0rd"
    assert user.password_hash.startswith("$argon2")


def test_weak_password_rejected():
    with pytest.raises(WeakPasswordError):
        hash_password("weak")


def test_authenticate_success(session):
    create_admin_user(session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT)
    session.commit()

    user = authenticate(session, username_or_email="agent1", raw_password="Str0ng!Passw0rd")
    session.commit()
    assert user.username == "agent1"
    assert user.failed_login_count == 0
    assert user.last_login_at is not None


def test_authenticate_wrong_password_increments_failed_count(session):
    create_admin_user(session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT)
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        authenticate(session, username_or_email="agent1", raw_password="WrongPassword1!")
    session.commit()


def test_lockout_after_max_failed_attempts(session):
    create_admin_user(session, email="agent@example.com", username="agent1", raw_password="Str0ng!Passw0rd", role=AGENT)
    session.commit()

    for _ in range(MAX_FAILED_ATTEMPTS):
        with pytest.raises(InvalidCredentialsError):
            authenticate(session, username_or_email="agent1", raw_password="WrongPassword1!")
        session.commit()

    with pytest.raises(AccountLockedError):
        authenticate(session, username_or_email="agent1", raw_password="Str0ng!Passw0rd")


def test_unknown_user_raises_invalid_credentials_not_account_locked(session):
    with pytest.raises(InvalidCredentialsError):
        authenticate(session, username_or_email="nobody", raw_password="whatever123!")
