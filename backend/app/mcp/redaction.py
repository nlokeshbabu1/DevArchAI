"""Secret redaction for the MCP layer.

Guarantees that no credentials, tokens, or other sensitive values ever leak
into MCP contexts that may be stored, cached, logged, or passed to an LLM.

Applied to every MCP payload before it is cached or returned.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"


class SecretRedactor:
    """Redacts well-known secret patterns from text and dict-like structures."""

    _PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
        # AWS access keys (AKIA/ASIA/ABIA/ACCA)
        (re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b"), "AWS_ACCESS_KEY"),
        # AWS secret key (40-char base64ish)
        (re.compile(r"\b(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40}(?![A-Za-z0-9+/])\b"), "AWS_SECRET"),
        # PEM private keys (multiline)
        (
            re.compile(
                r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
                re.DOTALL,
            ),
            "PRIVATE_KEY",
        ),
        # OpenSSH private keys
        (re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----.*?-----END OPENSSH PRIVATE KEY-----", re.DOTALL), "PRIVATE_KEY"),
        # JWT / JWS (header.payload.signature)
        (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "JWT"),
        # Bearer tokens
        (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE), "BEARER_TOKEN"),
        # GitHub tokens (ghp_, github_pat_, gho_, ghu_, ghs_)
        (re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]+\b"), "GITHUB_TOKEN"),
        # Stripe / payment keys
        (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"), "PAYMENT_KEY"),
        # Named secret assignments: KEY=value / KEY: value / KEY:value
        (
            re.compile(
                r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|"
                r"client[_-]?secret|access[_-]?key(?:[_ ]?id)?|private[_-]?key|"
                r"auth[_-]?token|session[_-]?key|connection[_-]?string|"
                r"jdbc[_-]?url|slack[_-]?(?:webhook|token))\b"
                r"\s*[:=]\s*\S+"
            ),
            "SECRET_ASSIGNMENT",
        ),
        # URLs with embedded credentials
        (
            re.compile(r"(?i)\b(?:[a-z][a-z0-9+.-]*://)([^/\s:@]+):([^/\s@]+)@"),
            "URL_CREDENTIALS",
        ),
        # Password in mongodb/postgres/redis DSN query strings
        (
            re.compile(r"(?i)\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|redis|mysql)://[^\s]+"),
            "DSN_WITH_CREDENTIALS",
        ),
    )

    def redact_text(self, text: str) -> str:
        """Return ``text`` with all detected secrets replaced."""
        for pattern, label in self._PATTERNS:
            text = pattern.sub(f"{REDACTED}:{label}" if label != "SECRET_ASSIGNMENT" else REDACTED, text)
        return text

    def redact(self, value: Any, *, _key: str = "") -> Any:
        """Recursively redact secrets inside a JSON-like structure.

        Strings matching secret patterns are replaced. Dict/list structures
        are traversed in place (a shallow copy is returned).
        """
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, dict):
            return {
                str(k): self.redact(v, _key=str(k))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.redact(v, _key=_key) for v in value]
        return value

    def is_safe(self, value: Any) -> bool:
        """True if the value contains no detectable secrets."""
        return self.redact(value) == value


# Singleton
_redactor: SecretRedactor | None = None


def get_redactor() -> SecretRedactor:
    """Get the global secret redactor singleton."""
    global _redactor
    if _redactor is None:
        _redactor = SecretRedactor()
    return _redactor


def redact_secrets(value: Any) -> Any:
    """Convenience wrapper around the singleton redactor."""
    return get_redactor().redact(value)
