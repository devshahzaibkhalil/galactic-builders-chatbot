import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.services.analytics_service import count_events, event_summary, track_event


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_track_event_creates_record(session):
    event = track_event(session, event_name="estimate_flow_started", conversation_id="conv-1")
    session.commit()
    assert event.id is not None
    assert event.event_name == "estimate_flow_started"


def test_count_events_counts_matching_name_only(session):
    track_event(session, event_name="estimate_flow_started")
    track_event(session, event_name="estimate_flow_started")
    track_event(session, event_name="photo_uploaded")
    session.commit()

    assert count_events(session, event_name="estimate_flow_started") == 2
    assert count_events(session, event_name="photo_uploaded") == 1
    assert count_events(session, event_name="bookmark_created") == 0


def test_event_summary_groups_by_name(session):
    track_event(session, event_name="estimate_flow_started")
    track_event(session, event_name="estimate_flow_started")
    track_event(session, event_name="photo_uploaded")
    session.commit()

    summary = event_summary(session)
    assert summary["estimate_flow_started"] == 2
    assert summary["photo_uploaded"] == 1


def test_metadata_stored_and_retrievable(session):
    event = track_event(session, event_name="photo_uploaded", metadata={"count": 3})
    session.commit()
    assert event.metadata_dict == {"count": 3}
