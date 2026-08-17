"""Encryption utilities for sensitive data."""

import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)

# Current encryption version for OAuth tokens
CURRENT_TOKEN_ENCRYPTION_VERSION = 1


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, encryption_key: str | None = None):
        """Initialize encryption service with a key."""
        # Use provided key or derive from SECRET_KEY
        if encryption_key:
            key = encryption_key.encode()
        else:
            # Derive a 32-byte key from SECRET_KEY for Fernet
            key = base64.urlsafe_b64encode(
                settings.SECRET_KEY.encode()[:32].ljust(32, b'\0')
            )

        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        if not plaintext:
            return plaintext
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        if not ciphertext:
            return ciphertext
        try:
            decrypted = self.fernet.decrypt(base64.urlsafe_b64decode(ciphertext.encode()))
            return decrypted.decode()
        except Exception as exc:
            if "@" not in ciphertext:
                logger.warning("Email decryption failed: %s", exc)
            return ciphertext


@lru_cache
def get_encryption_service() -> EncryptionService:
    """Get cached encryption service instance."""
    if not settings.ENCRYPTION_KEY:
        logger.warning(
            "ENCRYPTION_KEY is not set. Encryption key derived from SECRET_KEY. "
            "If SECRET_KEY changes, encrypted data (e.g. user emails) will be unrecoverable. "
            "Set ENCRYPTION_KEY in .env to a stable Fernet-compatible key."
        )
    return EncryptionService()


# Convenience functions for emails
def encrypt_email(email: str) -> str:
    """Encrypt an email address."""
    return get_encryption_service().encrypt(email)


def decrypt_email(encrypted_email: str) -> str:
    """Decrypt an email address."""
    return get_encryption_service().decrypt(encrypted_email)


# Convenience functions for OAuth tokens
def encrypt_oauth_token(token: str) -> str:
    """Encrypt an OAuth token (GitHub/GitLab access token).

    Args:
        token: The plaintext OAuth token.

    Returns:
        The encrypted token as a string.
    """
    if not token:
        return token
    return get_encryption_service().encrypt(token)


def decrypt_oauth_token(encrypted_token: str) -> str:
    """Decrypt an OAuth token.

    Args:
        encrypted_token: The encrypted token string.

    Returns:
        The decrypted plaintext token, or empty string on failure.
    """
    if not encrypted_token:
        return encrypted_token
    try:
        return get_encryption_service().decrypt(encrypted_token)
    except Exception as exc:
        logger.error("oauth_token_decryption_failed", error_type=type(exc).__name__)
        return ""


def get_user_oauth_token(user, provider: str) -> str:
    """Get decrypted OAuth token for a user.

    Args:
        user: The User model instance.
        provider: 'github' or 'gitlab'.

    Returns:
        The decrypted OAuth token, or empty string if not available.
    """
    if provider == "github":
        # Try encrypted column first, fall back to plaintext for migration
        if user.github_access_token_encrypted:
            return decrypt_oauth_token(user.github_access_token_encrypted)
        return user.github_access_token or ""
    elif provider == "gitlab":
        if user.gitlab_access_token_encrypted:
            return decrypt_oauth_token(user.gitlab_access_token_encrypted)
        return user.gitlab_access_token or ""
    return ""


def set_user_oauth_token(user, provider: str, token: str) -> None:
    """Set encrypted OAuth token for a user.

    Args:
        user: The User model instance.
        provider: 'github' or 'gitlab'.
        token: The plaintext OAuth token to encrypt and store.
    """
    if not token:
        return

    encrypted_token = encrypt_oauth_token(token)

    if provider == "github":
        user.github_access_token_encrypted = encrypted_token
        user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
        # Keep plaintext for backward compatibility during migration
        # Once migration is complete, set to None
        user.github_access_token = token
    elif provider == "gitlab":
        user.gitlab_access_token_encrypted = encrypted_token
        user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
        user.gitlab_access_token = token


def migrate_plaintext_token_to_encrypted(user, provider: str) -> bool:
    """Migrate a plaintext OAuth token to encrypted storage.

    This is used during the backfill migration to encrypt existing tokens.

    Args:
        user: The User model instance.
        provider: 'github' or 'gitlab'.

    Returns:
        True if migration was performed, False if already encrypted or no token.
    """
    if provider == "github":
        if user.github_access_token and not user.github_access_token_encrypted:
            encrypted_token = encrypt_oauth_token(user.github_access_token)
            user.github_access_token_encrypted = encrypted_token
            user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
            return True
    elif provider == "gitlab":
        if user.gitlab_access_token and not user.gitlab_access_token_encrypted:
            encrypted_token = encrypt_oauth_token(user.gitlab_access_token)
            user.gitlab_access_token_encrypted = encrypted_token
            user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
            return True
    return False
