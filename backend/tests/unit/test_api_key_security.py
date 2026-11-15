"""API key hashing and verification tests."""

from app.core.security import hash_token, is_stored_api_key_hash, verify_user_api_key


def test_verify_hashed_api_key():
    raw = "dk_abcd_secretvalue"
    stored = hash_token(raw)
    assert is_stored_api_key_hash(stored)
    assert verify_user_api_key(stored, raw)
    assert not verify_user_api_key(stored, "dk_abcd_wrong")


def test_verify_legacy_plaintext_api_key():
    raw = "dk_abcd_secretvalue"
    assert verify_user_api_key(raw, raw)
    assert not is_stored_api_key_hash(raw)
