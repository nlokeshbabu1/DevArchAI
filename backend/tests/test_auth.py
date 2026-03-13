"""
Authentication Tests

Tests for authentication logic, password hashing, and JWT tokens
"""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2")  # bcrypt hash prefix

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_different_for_same_password(self):
        """Test that same password produces different hashes."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestAccessToken:
    """Test access token creation and decoding."""

    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "test-user-id", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_access_token(self):
        """Test decoding valid access token."""
        data = {"sub": "test-user-id", "email": "test@example.com"}
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "test-user-id"
        assert payload["email"] == "test@example.com"

    def test_decode_expired_token(self):
        """Test decoding expired token."""
        data = {"sub": "test-user-id"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        payload = decode_token(token)
        assert payload is None

    def test_token_expiration(self):
        """Test token expiration time."""
        data = {"sub": "test-user-id"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = decode_token(token)
        assert payload is not None

        # Check exp claim exists
        assert "exp" in payload


class TestRefreshToken:
    """Test refresh token functionality."""

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": "test-user-id"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_refresh_token_longer_expiry(self):
        """Test refresh token has longer expiry than access token."""
        data = {"sub": "test-user-id"}

        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert refresh_payload["exp"] > access_payload["exp"]


class TestTokenEdgeCases:
    """Test token edge cases."""

    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        assert payload is None

    def test_decode_empty_token(self):
        """Test decoding empty token."""
        payload = decode_token("")
        assert payload is None

    def test_decode_none_token(self):
        """Test decoding None token."""
        payload = decode_token(None)
        assert payload is None

    def test_token_with_extra_claims(self):
        """Test token with extra claims."""
        data = {
            "sub": "test-user-id",
            "email": "test@example.com",
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
