"""PKCE helpers for CLI browser login."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_verifier(length: int = 64) -> str:
    """Return a URL-safe PKCE code verifier."""
    raw = secrets.token_urlsafe(length)
    return raw[:128]


def challenge_from_verifier(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    return secrets.token_urlsafe(32)