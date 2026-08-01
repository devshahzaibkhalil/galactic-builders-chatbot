import pytest

from app.security.encryption import DecryptionError, EncryptionKeyMissingError, decrypt, encrypt, generate_key
from app.services.encryption_service import compute_blind_index, decrypt_field, encrypt_field

KEY = generate_key()
BLIND_KEY = "blind-index-secret"


def test_encrypt_then_decrypt_roundtrips():
    ciphertext = encrypt("jordan@example.com", key=KEY)
    assert ciphertext != "jordan@example.com"
    assert decrypt(ciphertext, key=KEY) == "jordan@example.com"


def test_ciphertext_is_not_plaintext_substring():
    ciphertext = encrypt("sensitive value", key=KEY)
    assert "sensitive" not in ciphertext


def test_wrong_key_fails_to_decrypt():
    ciphertext = encrypt("jordan@example.com", key=KEY)
    other_key = generate_key()
    with pytest.raises(DecryptionError):
        decrypt(ciphertext, key=other_key)


def test_missing_key_raises():
    with pytest.raises(EncryptionKeyMissingError):
        encrypt("value", key="")
    with pytest.raises(EncryptionKeyMissingError):
        decrypt("value", key="")


def test_encrypt_field_service_wrapper_roundtrips():
    ciphertext = encrypt_field("574-555-0100", key=KEY)
    assert decrypt_field(ciphertext, key=KEY) == "574-555-0100"


def test_blind_index_is_deterministic():
    idx1 = compute_blind_index("jordan@example.com", blind_index_key=BLIND_KEY)
    idx2 = compute_blind_index("jordan@example.com", blind_index_key=BLIND_KEY)
    assert idx1 == idx2


def test_blind_index_normalizes_case_and_whitespace():
    idx1 = compute_blind_index("Jordan@Example.com", blind_index_key=BLIND_KEY)
    idx2 = compute_blind_index("  jordan@example.com  ", blind_index_key=BLIND_KEY)
    assert idx1 == idx2


def test_blind_index_differs_for_different_values():
    idx1 = compute_blind_index("jordan@example.com", blind_index_key=BLIND_KEY)
    idx2 = compute_blind_index("someone-else@example.com", blind_index_key=BLIND_KEY)
    assert idx1 != idx2


def test_blind_index_is_not_reversible_to_plaintext():
    idx = compute_blind_index("jordan@example.com", blind_index_key=BLIND_KEY)
    assert "jordan" not in idx
