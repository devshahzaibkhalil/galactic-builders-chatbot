import pytest

from app.core.conversation_store import DbConversationStore
from app.extensions import build_engine, build_session_factory, create_all


@pytest.fixture()
def session_factory():
    engine = build_engine("sqlite:///:memory:")
    import app.models  # noqa: F401 - register all models before create_all
    create_all(engine)
    return build_session_factory(engine)


def test_conversation_survives_a_fresh_store_instance(session_factory):
    store1 = DbConversationStore(session_factory)
    state = store1.get_or_create(None, session_id="s1")
    state.pending_field = "email"
    state.completed_fields["service_key"] = "kitchen_remodeling"
    store1.save(state)

    # A brand new store instance simulates the process having restarted —
    # if this were the in-memory store, this conversation would be gone.
    store2 = DbConversationStore(session_factory)
    reloaded = store2.get_or_create(state.conversation_id, session_id="s1")

    assert reloaded.pending_field == "email"
    assert reloaded.completed_fields["service_key"] == "kitchen_remodeling"


def test_exists_reflects_persisted_state(session_factory):
    store = DbConversationStore(session_factory)
    assert not store.exists("nonexistent-id")

    state = store.get_or_create(None, session_id="s1")
    assert store.exists(state.conversation_id)


def test_messages_are_persisted_to_the_transcript(session_factory):
    from app.repositories import conversation_repository

    store = DbConversationStore(session_factory)
    state = store.get_or_create(None, session_id="s1")

    db_session = session_factory()
    try:
        conversation_repository.append_message(
            db_session, conversation_id=state.conversation_id, sender_type="customer", content="Hello"
        )
        conversation_repository.append_message(
            db_session, conversation_id=state.conversation_id, sender_type="bot", content="Hi there"
        )
        db_session.commit()

        messages = conversation_repository.list_messages(db_session, state.conversation_id)
    finally:
        db_session.close()

    assert [m.sender_type for m in messages] == ["customer", "bot"]
    assert [m.content for m in messages] == ["Hello", "Hi there"]
