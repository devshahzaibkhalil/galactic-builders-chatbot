import pytest
from sqlalchemy import select, text

from app.extensions import build_engine, build_session_factory, create_all
from app.models.lead import InterestResponse, Lead, LeadStatus


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
        project_description="Replace cabinets.",
        email="jordan@example.com",
        phone="(574) 555-0100",
        interest_response=InterestResponse.YES,
        status=LeadStatus.NEW,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_email_property_roundtrips(session):
    lead = _make_lead()
    session.add(lead)
    session.commit()
    lead_id = lead.id

    session.expunge(lead)
    reloaded = session.get(Lead, lead_id)
    assert reloaded.email == "jordan@example.com"
    assert reloaded.phone == "(574) 555-0100"


def test_raw_stored_ciphertext_is_not_the_plaintext(session):
    lead = _make_lead()
    session.add(lead)
    session.commit()

    # Read the raw column value directly, bypassing the property, to prove
    # what's actually sitting in the database.
    raw_email_column = session.execute(
        text("SELECT email_ciphertext FROM leads WHERE id = :id"), {"id": lead.id}
    ).scalar_one()

    assert raw_email_column != "jordan@example.com"
    assert "jordan" not in raw_email_column
    assert "example.com" not in raw_email_column


def test_blind_index_enables_lookup_without_plaintext_query(session):
    lead = _make_lead(email="unique-lookup-test@example.com")
    session.add(lead)
    session.commit()

    blind_index = Lead.email_lookup_index("unique-lookup-test@example.com")
    found = session.execute(select(Lead).where(Lead.email_blind_index == blind_index)).scalar_one()
    assert found.id == lead.id
    assert found.email == "unique-lookup-test@example.com"


def test_null_email_handled_gracefully(session):
    lead = _make_lead(email=None, phone=None)
    session.add(lead)
    session.commit()
    assert lead.email is None
    assert lead.email_ciphertext is None
    assert lead.email_blind_index is None
