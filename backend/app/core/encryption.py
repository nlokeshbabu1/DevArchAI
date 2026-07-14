"""Encryption utilities for sensitive data."""

import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)


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


# Convenience functions
def encrypt_email(email: str) -> str:
    """Encrypt an email address."""
    return get_encryption_service().encrypt(email)


def decrypt_email(encrypted_email: str) -> str:
    """Decrypt an email address."""
    return get_encryption_service().decrypt(encrypted_email)
