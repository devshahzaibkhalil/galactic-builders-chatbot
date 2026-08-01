import pytest
from pydantic import ValidationError

from app.schemas.service_faq_schema import ServiceFaqFile


def _valid_payload(**overrides):
    payload = {
        "service_key": "kitchen_remodeling",
        "display_name": "Kitchen Remodeling",
        "category": "interior_remodeling",
        "enabled": True,
        "aliases": ["kitchen renovation"],
        "summary": "Galactic Builders can review kitchen remodeling projects.",
        "restricted_claims": ["Do not provide a fixed price."],
        "faqs": [
            {
                "id": "kitchen-remodeling-001",
                "question": "Do you provide kitchen remodeling services?",
                "answer": "Yes. The team must review your required work before confirming scope.",
                "keywords": ["kitchen remodeling"],
                "intent": "service_availability",
                "follow_up_action": "offer_estimate_flow",
            }
        ],
        "lead_questions": ["Are you planning a full remodel or selected updates?"],
    }
    payload.update(overrides)
    return payload


def test_valid_file_parses():
    ServiceFaqFile.model_validate(_valid_payload())


def test_rejects_duplicate_faq_ids():
    payload = _valid_payload()
    payload["faqs"].append(dict(payload["faqs"][0]))
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_faq_id_from_another_service():
    payload = _valid_payload()
    payload["faqs"][0]["id"] = "roof-repair-001"
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_fixed_price_in_answer():
    payload = _valid_payload()
    payload["faqs"][0]["answer"] = "This project costs $4,500 flat rate."
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_guaranteed_completion_date():
    payload = _valid_payload()
    payload["faqs"][0]["answer"] = "We guarantee completion by next Friday."
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_script_content():
    payload = _valid_payload()
    payload["faqs"][0]["answer"] = "Sure <script>alert(1)</script>"
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_empty_question():
    payload = _valid_payload()
    payload["faqs"][0]["question"] = "   "
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)


def test_rejects_unsupported_intent():
    payload = _valid_payload()
    payload["faqs"][0]["intent"] = "not_a_real_intent"
    with pytest.raises(ValidationError):
        ServiceFaqFile.model_validate(payload)
