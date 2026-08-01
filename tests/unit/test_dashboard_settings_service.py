import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.services.dashboard_settings_service import InvalidColorError, get_theme, reset_theme, update_theme


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_default_theme_returned_when_none_set(session):
    theme = get_theme(session)
    assert theme.primary_color == "#0d2238"
    assert theme.accent_color == "#d2a33b"


def test_update_theme_persists(session):
    update_theme(session, primary_color="#112233", accent_color="#aabbcc")
    session.commit()

    reloaded = get_theme(session)
    assert reloaded.primary_color == "#112233"
    assert reloaded.accent_color == "#aabbcc"


def test_invalid_color_rejected(session):
    with pytest.raises(InvalidColorError):
        update_theme(session, primary_color="not-a-color", accent_color="#aabbcc")


def test_reset_restores_defaults(session):
    update_theme(session, primary_color="#112233", accent_color="#aabbcc")
    session.commit()
    reset_theme(session)
    session.commit()

    reloaded = get_theme(session)
    assert reloaded.primary_color == "#0d2238"
    assert reloaded.accent_color == "#d2a33b"
