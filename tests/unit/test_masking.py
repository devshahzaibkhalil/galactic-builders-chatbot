from app.utils.masking import mask_email, mask_phone, mask_street_address


def test_mask_email_typical():
    assert mask_email("jordan@example.com") == "j****n@example.com"


def test_mask_email_short_local_part():
    result = mask_email("jo@example.com")
    assert result.endswith("@example.com")
    assert "jo" not in result


def test_mask_email_no_at_sign_returned_unchanged():
    assert mask_email("not-an-email") == "not-an-email"


def test_mask_phone_shows_last_four_only():
    assert mask_phone("(574) 555-0100") == "(***) ***-0100"


def test_mask_phone_handles_plain_digits():
    assert mask_phone("5745550100") == "(***) ***-0100"


def test_mask_street_address_keeps_house_number_only():
    assert mask_street_address("123 Main St") == "123 ***"


def test_mask_street_address_empty():
    assert mask_street_address("") == ""
