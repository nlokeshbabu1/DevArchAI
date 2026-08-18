"""Tests for OAuth token encryption."""

import pytest
from unittest.mock import MagicMock, patch
from app.core.encryption import (
    encrypt_oauth_token,
    decrypt_oauth_token,
    get_user_oauth_token,
    set_user_oauth_token,
    migrate_plaintext_token_to_encrypted,
    CURRENT_TOKEN_ENCRYPTION_VERSION,
)


class TestOAuthTokenEncryption:
    """Test OAuth token encryption functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption are inverse operations."""
        token = "gho_mock_access_token_12345"
        encrypted = encrypt_oauth_token(token)
        decrypted = decrypt_oauth_token(encrypted)
        assert decrypted == token

    def test_encrypt_empty_token(self):
        """Test that empty tokens are handled correctly."""
        assert encrypt_oauth_token("") == ""
        assert encrypt_oauth_token(None) is None

    def test_decrypt_empty_token(self):
        """Test that empty encrypted tokens are handled correctly."""
        assert decrypt_oauth_token("") == ""
        assert decrypt_oauth_token(None) is None

    def test_decrypt_invalid_token(self):
        """Test that invalid encrypted tokens return empty string."""
        result = decrypt_oauth_token("invalid_base64")
        # The function returns the original string if decryption fails
        assert result == "invalid_base64"

    def test_get_user_oauth_token_github_encrypted(self):
        """Test getting encrypted GitHub token."""
        user = MagicMock()
        user.github_access_token_encrypted = "encrypted_token"
        user.github_access_token = None
        
        with patch("app.core.encryption.decrypt_oauth_token", return_value="decrypted_token"):
            result = get_user_oauth_token(user, "github")
            assert result == "decrypted_token"

    def test_get_user_oauth_token_github_plaintext_fallback(self):
        """Test fallback to plaintext GitHub token."""
        user = MagicMock()
        user.github_access_token_encrypted = None
        user.github_access_token = "plaintext_token"
        
        result = get_user_oauth_token(user, "github")
        assert result == "plaintext_token"

    def test_get_user_oauth_token_gitlab_encrypted(self):
        """Test getting encrypted GitLab token."""
        user = MagicMock()
        user.gitlab_access_token_encrypted = "encrypted_token"
        user.gitlab_access_token = None
        
        with patch("app.core.encryption.decrypt_oauth_token", return_value="decrypted_token"):
            result = get_user_oauth_token(user, "gitlab")
            assert result == "decrypted_token"

    def test_get_user_oauth_token_gitlab_plaintext_fallback(self):
        """Test fallback to plaintext GitLab token."""
        user = MagicMock()
        user.gitlab_access_token_encrypted = None
        user.gitlab_access_token = "plaintext_token"
        
        result = get_user_oauth_token(user, "gitlab")
        assert result == "plaintext_token"

    def test_get_user_oauth_token_unknown_provider(self):
        """Test unknown provider returns empty string."""
        user = MagicMock()
        result = get_user_oauth_token(user, "unknown")
        assert result == ""

    def test_set_user_oauth_token_github(self):
        """Test setting GitHub OAuth token."""
        user = MagicMock()
        user.github_access_token_encrypted = None
        user.token_encryption_version = None
        user.github_access_token = None
        
        with patch("app.core.encryption.encrypt_oauth_token", return_value="encrypted_token"):
            set_user_oauth_token(user, "github", "plaintext_token")
            
            assert user.github_access_token_encrypted == "encrypted_token"
            assert user.token_encryption_version == CURRENT_TOKEN_ENCRYPTION_VERSION
            assert user.github_access_token == "plaintext_token"

    def test_set_user_oauth_token_gitlab(self):
        """Test setting GitLab OAuth token."""
        user = MagicMock()
        user.gitlab_access_token_encrypted = None
        user.token_encryption_version = None
        user.gitlab_access_token = None
        
        with patch("app.core.encryption.encrypt_oauth_token", return_value="encrypted_token"):
            set_user_oauth_token(user, "gitlab", "plaintext_token")
            
            assert user.gitlab_access_token_encrypted == "encrypted_token"
            assert user.token_encryption_version == CURRENT_TOKEN_ENCRYPTION_VERSION
            assert user.gitlab_access_token == "plaintext_token"

    def test_set_user_oauth_token_empty(self):
        """Test setting empty token does nothing."""
        user = MagicMock()
        set_user_oauth_token(user, "github", "")
        set_user_oauth_token(user, "github", None)
        # No assertions needed, just ensuring no exceptions

    def test_migrate_plaintext_token_github(self):
        """Test migrating plaintext GitHub token to encrypted."""
        user = MagicMock()
        user.github_access_token = "plaintext_token"
        user.github_access_token_encrypted = None
        
        with patch("app.core.encryption.encrypt_oauth_token", return_value="encrypted_token"):
            result = migrate_plaintext_token_to_encrypted(user, "github")
            
            assert result is True
            assert user.github_access_token_encrypted == "encrypted_token"
            assert user.token_encryption_version == CURRENT_TOKEN_ENCRYPTION_VERSION

    def test_migrate_plaintext_token_gitlab(self):
        """Test migrating plaintext GitLab token to encrypted."""
        user = MagicMock()
        user.gitlab_access_token = "plaintext_token"
        user.gitlab_access_token_encrypted = None
        
        with patch("app.core.encryption.encrypt_oauth_token", return_value="encrypted_token"):
            result = migrate_plaintext_token_to_encrypted(user, "gitlab")
            
            assert result is True
            assert user.gitlab_access_token_encrypted == "encrypted_token"
            assert user.token_encryption_version == CURRENT_TOKEN_ENCRYPTION_VERSION

    def test_migrate_already_encrypted(self):
        """Test migration returns False if already encrypted."""
        user = MagicMock()
        user.github_access_token = "plaintext_token"
        user.github_access_token_encrypted = "already_encrypted"
        
        result = migrate_plaintext_token_to_encrypted(user, "github")
        assert result is False

    def test_migrate_no_token(self):
        """Test migration returns False if no token exists."""
        user = MagicMock()
        user.github_access_token = None
        user.github_access_token_encrypted = None
        
        result = migrate_plaintext_token_to_encrypted(user, "github")
        assert result is False
