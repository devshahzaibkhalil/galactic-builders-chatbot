from pathlib import Path

import pytest

from app.services.knowledge_service import KnowledgeService
from app.validators.address_validator import validate_street_address
from app.validators.location_validator import validate_city, validate_state
from app.validators.project_validator import validate_project_description
from app.validators.service_validator import validate_service_key

FAQ_ROOT = Path(__file__).resolve().parents[2] / "app" / "data" / "faqs"


def test_valid_address_accepted():
    r = validate_street_address("123 Main St")
    assert r["valid"]


def test_address_without_number_rejected():
    r = validate_street_address("Main Street")
    assert not r["valid"]
    assert r["error_code"] == "address_missing_number"


def test_address_with_header_injection_rejected():
    r = validate_street_address("123 Main St\r\nBcc: attacker@evil.com")
    assert not r["valid"]


def test_valid_city():
    assert validate_city("South Bend")["valid"]


def test_invalid_city_with_digits():
    assert not validate_city("South Bend 2")["valid"]


def test_valid_state_abbreviation():
    r = validate_state("in")
    assert r["valid"]
    assert r["normalized_value"] == "IN"


def test_invalid_state_full_name_rejected():
    assert not validate_state("Indiana")["valid"]


def test_project_description_too_short():
    r = validate_project_description("hi")
    assert not r["valid"]
    assert r["error_code"] == "project_description_too_short"


def test_project_description_too_long():
    r = validate_project_description("x" * 2001)
    assert not r["valid"]
    assert r["error_code"] == "project_description_too_long"


def test_project_description_valid():
    assert validate_project_description("Replace kitchen cabinets and countertops.")["valid"]


@pytest.fixture()
def knowledge_service():
    ks = KnowledgeService(faq_root=FAQ_ROOT)
    ks.load(strict=True)
    return ks


def test_service_key_valid_when_enabled(knowledge_service):
    r = validate_service_key("kitchen_remodeling", knowledge_service)
    assert r["valid"]


def test_service_key_normalizes_dashes_and_spaces(knowledge_service):
    r = validate_service_key("kitchen-remodeling", knowledge_service)
    assert r["valid"]
    assert r["normalized_value"] == "kitchen_remodeling"


def test_service_key_invalid_when_not_in_catalog(knowledge_service):
    r = validate_service_key("solar_panel_installation", knowledge_service)
    assert not r["valid"]
    assert r["error_code"] == "service_not_available"
