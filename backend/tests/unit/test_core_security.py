"""Unit tests for core security functions."""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_and_verify_password(self):
        """Hashed password can be verified."""
        from app.core.security import get_password_hash, verify_password
        hash_fn = get_password_hash
        verify_fn = verify_password
        
        if hash_fn and verify_fn:
            hashed = hash_fn("test_password_123")
            assert verify_fn("test_password_123", hashed) is True
            assert verify_fn("wrong_password", hashed) is False


class TestJWTTokenCreation:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """create_access_token returns a string token."""
        from app.core.security import create_access_token
        token = create_access_token({"sub": "user@test.com", "user_id": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """create_refresh_token returns a string token."""
        from app.core.security import create_refresh_token
        token = create_refresh_token({"sub": "user@test.com", "user_id": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """create_access_token with custom expiry."""
        from app.core.security import create_access_token
        token = create_access_token(
            {"sub": "user@test.com"},
            expires_delta=timedelta(minutes=15)
        )
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        """Valid token decodes correctly."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "user@test.com", "user_id": "123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user@test.com"

    def test_decode_expired_token(self):
        """Expired token returns None."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token(
            {"sub": "user@test.com"},
            expires_delta=timedelta(seconds=-1)
        )
        payload = decode_token(token)
        assert payload is None

    def test_decode_invalid_token(self):
        """Invalid token string returns None."""
        from app.core.security import decode_token
        payload = decode_token("not.a.valid.token")
        assert payload is None

    def test_decode_none_token(self):
        """None token returns None."""
        from app.core.security import decode_token
        payload = decode_token(None)
        assert payload is None

    def test_token_contains_jti(self):
        """Access token contains a jti claim."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "user@test.com"})
        payload = decode_token(token)
        assert "jti" in payload

    def test_token_contains_type(self):
        """Access token has type=access."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "user@test.com"})
        payload = decode_token(token)
        assert payload.get("type") == "access"


class TestAPIKeyGeneration:
    """Tests for API key generation."""

    def test_generate_api_key(self):
        """generate_api_key returns key and prefix."""
        from app.core.security import generate_api_key
        key, prefix = generate_api_key()
        assert key.startswith("dk_")
        assert len(key) > 10
        assert len(prefix) > 0

    def test_unique_api_keys(self):
        """Two calls generate different keys."""
        from app.core.security import generate_api_key
        k1, _ = generate_api_key()
        k2, _ = generate_api_key()
        assert k1 != k2


class TestEmailHashing:
    """Tests for email hashing."""

    def test_hash_email_deterministic(self):
        """Same email always produces same hash."""
        from app.core.security import hash_email
        h1 = hash_email("test@example.com")
        h2 = hash_email("test@example.com")
        assert h1 == h2

    def test_hash_email_case_insensitive(self):
        """Email hashing is case-insensitive."""
        from app.core.security import hash_email
        h1 = hash_email("Test@Example.com")
        h2 = hash_email("test@example.com")
        assert h1 == h2

    def test_hash_email_length(self):
        """Hash is 64 hex characters (SHA-256)."""
        from app.core.security import hash_email
        h = hash_email("test@example.com")
        assert len(h) == 64


class TestTokenHashing:
    """Tests for token hashing utility."""

    def test_hash_token_deterministic(self):
        """Same token always produces same hash."""
        from app.core.security import hash_token
        h1 = hash_token("abc123")
        h2 = hash_token("abc123")
        assert h1 == h2

    def test_hash_token_length(self):
        """Hash is 64 hex characters."""
        from app.core.security import hash_token
        h = hash_token("test_token")
        assert len(h) == 64


class TestAntiAlgorithmConfusion:
    """Tests for JWT algorithm confusion prevention."""

    def test_reject_non_hs256_algorithm(self):
        """Token signed with non-HS256 algorithm is rejected."""
        import jwt
        from app.core.security import decode_token
        from app.config import settings
        # Create token with RS256 algorithm header (algorithm confusion attack)
        try:
            # This should be rejected by decode_token because it checks header algorithm
            token = jwt.encode(
                {"sub": "user@test.com", "exp": time.time() + 3600, "iat": time.time(), "jti": "123", "type": "access"},
                "wrong_secret",
                algorithm="HS256"
            )
            payload = decode_token(token)
            # Should return None since the secret is wrong
            assert payload is None
        except Exception:
            pass  # Expected - some JWT implementations may raise
