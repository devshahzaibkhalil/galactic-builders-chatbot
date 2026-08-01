from app.services.lead_scoring_service import (
    PriorityLabel,
    calculate_priority_label,
    calculate_readiness,
)

COMPLETE_LEAD = {
    "service_key": "roof_repair",
    "project_description": "Leak near chimney flashing.",
    "city": "South Bend",
    "state": "IN",
    "zip_code": "46601",
    "timeline": "within_1_month",
    "budget_range": "5000_10000",
    "full_name": "Alex Rivera",
    "email": "alex@example.com",
    "phone": "(574) 555-0100",
    "preferred_contact_method": "phone",
    "photo_count": 3,
}


def test_fully_complete_lead_is_100_percent():
    result = calculate_readiness(COMPLETE_LEAD)
    assert result["readiness_percent"] == 100
    assert result["project_details"] == "Complete"
    assert result["location"] == "Complete"
    assert result["timeline"] == "Complete"
    assert result["contact_details"] == "Complete"
    assert result["photos"] == "Complete"


def test_missing_contact_details_marks_that_section_incomplete():
    lead = dict(COMPLETE_LEAD)
    lead["email"] = None
    result = calculate_readiness(lead)
    assert result["contact_details"] == "Incomplete"
    assert result["readiness_percent"] < 100


def test_no_photos_is_optional_not_incomplete():
    lead = dict(COMPLETE_LEAD)
    lead["photo_count"] = 0
    result = calculate_readiness(lead)
    assert result["photos"] == "Optional"


def test_empty_lead_is_zero_percent():
    result = calculate_readiness({})
    assert result["readiness_percent"] == 0


def test_priority_label_for_complete_lead_with_photos_and_timeline():
    lead = dict(COMPLETE_LEAD)
    assert calculate_priority_label(lead) == PriorityLabel.PRIORITY


def test_priority_label_incomplete_for_sparse_lead():
    lead = {"service_key": "roof_repair"}
    assert calculate_priority_label(lead) == PriorityLabel.INCOMPLETE


def test_safety_flag_forces_priority_regardless_of_completeness():
    lead = dict(COMPLETE_LEAD)
    lead["photo_count"] = 0
    lead["safety_flag"] = True
    assert calculate_priority_label(lead) == PriorityLabel.PRIORITY
