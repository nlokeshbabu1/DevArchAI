"""Shared input validation helpers (UUID parsing, repository URL/branch checks)."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException, status

_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9_./-]+$")
_URL_BLOCKLIST = re.compile(r"['\"\\;<>]")
_ALLOWED_GIT_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")
_FORBIDDEN_HOST_SUFFIXES = (".local", ".internal", ".localhost")
_LOOPBACK_NETS = (ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("::1/128"))


def parse_uuid(value: str, field_name: str = "id") -> UUID:
    """Parse a string as a UUID or raise HTTP 400 for invalid input."""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format. Expected UUID.",
        ) from exc


def validate_repository_url(value: str) -> str:
    """Validate that a repository URL is an HTTPS URL from a supported provider.

    Raises ValueError (for pydantic field_validator use) on invalid input.
    """
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValueError("Repository URL must use HTTPS")
    if not parsed.netloc:
        raise ValueError("Repository URL must include a host")
    host = parsed.netloc.lower()
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in _ALLOWED_GIT_HOSTS):
        raise ValueError("Repository URL must be from a supported provider")
    if _URL_BLOCKLIST.search(value):
        raise ValueError("Repository URL contains invalid characters")
    return value


def validate_branch(value: str) -> str:
    """Validate a git branch name."""
    value = value.strip()
    if not value:
        raise ValueError("Branch must not be empty")
    if len(value) > 100:
        raise ValueError("Branch name too long")
    if not _BRANCH_PATTERN.match(value):
        raise ValueError("Branch contains invalid characters")
    return value


def _is_private_address(host: str) -> bool:
    """Check whether a host resolves to a private, loopback, or link-local address."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    seen = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        ip = ipaddress.ip_address(addr)
        if not ip.is_global:
            return True
    return False


def validate_external_https_url(value: str, *, field_name: str = "url") -> str:
    """Validate an outbound HTTPS URL for SSRF protection.

    Ensures the URL is HTTPS, uses a standard port, does not embed credentials,
    and does not resolve to a private/loopback/link-local address.
    """
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValueError(f"{field_name} must be an HTTPS URL")
    if not parsed.netloc:
        raise ValueError(f"{field_name} must include a host")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not contain embedded credentials")
    if parsed.port is not None and parsed.port != 443:
        raise ValueError(f"{field_name} must use the standard HTTPS port")

    host = parsed.hostname or ""
    host_lower = host.lower()
    if not host_lower or host_lower in ("localhost", "::1", "0.0.0.0"):
        raise ValueError(f"{field_name} must not target internal hosts")
    if any(host_lower == suffix or host_lower.endswith(suffix) for suffix in _FORBIDDEN_HOST_SUFFIXES):
        raise ValueError(f"{field_name} must not target internal hosts")

    try:
        ip = ipaddress.ip_address(host_lower)
        if not ip.is_global:
            raise ValueError(f"{field_name} must not target internal hosts")
    except ValueError:
        pass

    if _is_private_address(host_lower):
        raise ValueError(f"{field_name} must not target internal hosts")

    if _URL_BLOCKLIST.search(value):
        raise ValueError(f"{field_name} contains invalid characters")
    return value
