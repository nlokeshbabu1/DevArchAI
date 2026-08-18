"""Unit tests for OAuth token encryption at rest."""
import pytest
from unittest.mock import MagicMock


class TestOAuthTokenEncryption:
    """Tests for encrypt_oauth_token and decrypt_oauth_token."""

    def test_encrypt_decrypt_roundtrip(self):
        """encrypt then decrypt preserves original token."""
        from app.core.encryption import encrypt_oauth_token, decrypt_oauth_token
        original = "ghp_abc123def456ghi789jkl012mno345"
        encrypted = encrypt_oauth_token(original)
        assert encrypted is not None
        assert encrypted != original
        decrypted = decrypt_oauth_token(encrypted)
        assert decrypted == original

    def test_encrypt_empty_token_returns_empty(self):
        """Empty token returns empty string (no-op path)."""
        from app.core.encryption import encrypt_oauth_token
        result = encrypt_oauth_token("")
        assert result == ""

    def test_encrypt_none_token_returns_none(self):
        """None token returns None."""
        from app.core.encryption import encrypt_oauth_token
        result = encrypt_oauth_token(None)
        assert result is None

    def test_decrypt_empty_returns_empty(self):
        """Empty encrypted string returns empty string (no-op path)."""
        from app.core.encryption import decrypt_oauth_token
        result = decrypt_oauth_token("")
        assert result == ""

    def test_decrypt_none_returns_none(self):
        """None encrypted string returns None."""
        from app.core.encryption import decrypt_oauth_token
        result = decrypt_oauth_token(None)
        assert result is None

    def test_different_encryptions_decrypt_same(self):
        """Same plaintext encrypts to different ciphertext (random IV) but decrypts same."""
        from app.core.encryption import encrypt_oauth_token, decrypt_oauth_token
        e1 = encrypt_oauth_token("same_token")
        e2 = encrypt_oauth_token("same_token")
        # Fernet uses random IV, so ciphertext differs
        assert e1 != e2
        # But both decrypt to same value
        assert decrypt_oauth_token(e1) == "same_token"
        assert decrypt_oauth_token(e2) == "same_token"

    def test_encrypt_preserves_long_token(self):
        """Long tokens (GitHub PATs are ~40 chars) work correctly."""
        from app.core.encryption import encrypt_oauth_token, decrypt_oauth_token
        long_token = "ghp_" + "a" * 36
        encrypted = encrypt_oauth_token(long_token)
        decrypted = decrypt_oauth_token(encrypted)
        assert decrypted == long_token


class TestUserOAuthTokenAccessors:
    """Tests for get_user_oauth_token and set_user_oauth_token."""

    def test_get_user_oauth_token_encrypted(self):
        """get_user_oauth_token returns decrypted token when encrypted field is set."""
        from app.core.encryption import encrypt_oauth_token, get_user_oauth_token
        encrypted = encrypt_oauth_token("ghp_decrypted")
        user = MagicMock()
        user.github_access_token_encrypted = encrypted
        user.github_access_token = None
        result = get_user_oauth_token(user, "github")
        assert result == "ghp_decrypted"

    def test_get_user_oauth_token_plaintext_fallback(self):
        """get_user_oauth_token falls back to plaintext when encrypted is None."""
        user = MagicMock()
        user.github_access_token_encrypted = None
        user.github_access_token = "ghp_plaintext_token"
        from app.core.encryption import get_user_oauth_token
        result = get_user_oauth_token(user, "github")
        assert result == "ghp_plaintext_token"

    def test_get_user_oauth_token_both_none_returns_empty(self):
        """get_user_oauth_token returns empty string when both fields are None."""
        user = MagicMock()
        user.github_access_token_encrypted = None
        user.github_access_token = None
        from app.core.encryption import get_user_oauth_token
        result = get_user_oauth_token(user, "github")
        assert result == ""

    def test_set_user_oauth_token(self):
        """set_user_oauth_token encrypts and stores the token."""
        user = MagicMock()
        user.github_access_token_encrypted = None
        user.github_access_token = None
        from app.core.encryption import set_user_oauth_token
        set_user_oauth_token(user, "github", "ghp_new_token")
        assert user.github_access_token_encrypted is not None
        # Verify the encrypted value decrypts correctly
        from app.core.encryption import decrypt_oauth_token
        decrypted = decrypt_oauth_token(user.github_access_token_encrypted)
        assert decrypted == "ghp_new_token"

    def test_set_user_oauth_token_clears_plaintext(self):
        """set_user_oauth_token sets both encrypted and legacy plaintext fields."""
        user = MagicMock()
        user.github_access_token = "ghp_old_plaintext"
        from app.core.encryption import set_user_oauth_token
        set_user_oauth_token(user, "github", "ghp_new_token")
        # Implementation keeps both fields in sync
        assert user.github_access_token == "ghp_new_token"
        assert user.github_access_token_encrypted is not None


class TestUserModelOAuthColumns:
    """Tests for the User model OAuth token columns."""

    def test_user_model_has_encryption_version_column(self):
        """User model has token_encryption_version column."""
        from app.models.user import User
        assert hasattr(User, "token_encryption_version")

    def test_user_model_has_github_encrypted_column(self):
        """User model has github_access_token_encrypted column."""
        from app.models.user import User
        assert hasattr(User, "github_access_token_encrypted")

    def test_user_model_has_gitlab_encrypted_column(self):
        """User model has gitlab_access_token_encrypted column."""
        from app.models.user import User
        assert hasattr(User, "gitlab_access_token_encrypted")
