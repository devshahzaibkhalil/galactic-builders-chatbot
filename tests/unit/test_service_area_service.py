from app.services.service_area_service import ServiceAreaService


def test_approved_zip_confirmed():
    svc = ServiceAreaService()
    result = svc.check(zip_code="46601")
    assert result["status"] == "confirmed"


def test_unapproved_but_valid_zip_marked_outside_area():
    svc = ServiceAreaService()
    result = svc.check(zip_code="90210")
    assert result["status"] == "outside_area"


def test_approved_city_confirmed():
    svc = ServiceAreaService()
    result = svc.check(city="South Bend")
    assert result["status"] == "confirmed"


def test_city_matching_is_case_insensitive():
    svc = ServiceAreaService()
    result = svc.check(city="mishawaka")
    assert result["status"] == "confirmed"


def test_no_input_is_unconfirmed_not_a_guess():
    svc = ServiceAreaService()
    result = svc.check()
    assert result["status"] == "unconfirmed"


def test_garbage_zip_is_unconfirmed_not_outside_area():
    svc = ServiceAreaService()
    result = svc.check(zip_code="abc")
    assert result["status"] == "unconfirmed"


def test_zip_takes_precedence_and_is_checked_first():
    svc = ServiceAreaService()
    result = svc.check(zip_code="46601", city="Chicago")
    assert result["status"] == "confirmed"
