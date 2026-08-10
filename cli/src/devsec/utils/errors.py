"""Structured error handling with deterministic exit codes.

Exit codes are part of the public, CI-facing contract of the CLI and must
never change without a coordinated release:

0 = success / no policy violation
1 = policy violation / findings above configured threshold
2 = CLI usage error
3 = authentication error
4 = API error
5 = scan failure
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    """Deterministic process exit codes used across the CLI."""

    SUCCESS = 0
    POLICY_VIOLATION = 1
    USAGE = 2
    AUTH = 3
    API = 4
    SCAN_FAILURE = 5


class DevSecError(Exception):
    """Base class for all expected CLI errors.

    Every expected error carries a stable ``exit_code`` and a user-friendly
    ``hint`` (optional remediation text). ``str(exc)`` must never contain
    secrets or tokens.
    """

    exit_code: ExitCode = ExitCode.USAGE

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        return self.message


class UsageError(DevSecError):
    """Invalid command line usage. Maps to exit code 2."""

    exit_code = ExitCode.USAGE


class ApiFailureError(DevSecError):
    """An error that occurred while talking to the backend API.

    Carries the HTTP status, the backend's ``X-Request-ID`` (when present),
    and the failing request's method/URL for debugging - never the token.
    """

    exit_code = ExitCode.API

    def __init__(
        self,
        message: str,
        hint: str | None = None,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        method: str | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message, hint=hint)
        self.status_code = status_code
        self.request_id = request_id
        self.method = method
        self.url = url


class ApiError(ApiFailureError):
    """The API was reachable but returned an error. Maps to exit code 4."""


class AuthError(ApiFailureError):
    """Authentication or authorization failure. Maps to exit code 3."""

    exit_code = ExitCode.AUTH


class PolicyViolationError(DevSecError):
    """Findings exceeded the configured fail-on threshold. Maps to exit code 1."""

    exit_code = ExitCode.POLICY_VIOLATION


class ScanError(DevSecError):
    """A scan failed. Maps to exit code 5."""

    exit_code = ExitCode.SCAN_FAILURE


class ConfigError(UsageError):
    """Invalid or missing local configuration."""


def error_detail(exc: BaseException) -> dict[str, Any]:
    """Return a JSON-serializable representation of a handled error."""
    if isinstance(exc, ApiError):
        detail: dict[str, Any] = {
            "error": "api_error",
            "message": exc.message,
            "exit_code": int(exc.exit_code),
        }
        if exc.status_code is not None:
            detail["status_code"] = exc.status_code
        if exc.request_id:
            detail["request_id"] = exc.request_id
        return detail
    if isinstance(exc, DevSecError):
        return {
            "error": type(exc).__name__.replace("Error", "").lower(),
            "message": exc.message,
            "exit_code": int(exc.exit_code),
        }
    return {
        "error": "unexpected",
        "message": str(exc),
        "exit_code": int(ExitCode.USAGE),
    }
