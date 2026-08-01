from app.validators.file_validator import MAX_FILE_BYTES, validate_upload

PNG_BYTES = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"0" * 100
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj" + b"0" * 100
PHP_PAYLOAD = b'<?php system($_GET["c"]); ?>' + b"0" * 100


def test_valid_png_accepted():
    result = validate_upload("kitchen.png", PNG_BYTES)
    assert result["valid"]
    assert result["normalized_value"] == "image/png"


def test_valid_pdf_accepted():
    result = validate_upload("inspection.pdf", PDF_BYTES)
    assert result["valid"]


def test_extension_attack_php_disguised_as_jpg():
    """A PHP payload renamed to .jpg must be rejected by content sniffing,
    not accepted just because the filename looks safe."""
    result = validate_upload("photo.jpg", PHP_PAYLOAD)
    assert not result["valid"]
    assert result["error_code"] in ("mime_type_mismatch", "dangerous_content_detected")


def test_disallowed_extension_rejected():
    result = validate_upload("malware.exe", PHP_PAYLOAD)
    assert not result["valid"]
    assert result["error_code"] == "extension_not_allowed"


def test_mime_type_mismatch_pdf_renamed_to_png():
    result = validate_upload("fake.png", PDF_BYTES)
    assert not result["valid"]
    assert result["error_code"] == "mime_type_mismatch"


def test_oversized_file_rejected():
    oversized = PNG_BYTES + b"0" * (MAX_FILE_BYTES + 1)
    result = validate_upload("huge.png", oversized)
    assert not result["valid"]
    assert result["error_code"] == "file_too_large"


def test_empty_file_rejected():
    result = validate_upload("empty.png", b"")
    assert not result["valid"]
    assert result["error_code"] == "file_empty"


def test_missing_filename_rejected():
    result = validate_upload("", PNG_BYTES)
    assert not result["valid"]
    assert result["error_code"] == "filename_required"
