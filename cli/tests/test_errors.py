"""Tests for exit codes and structured error serialization."""

from __future__ import annotations

import json

import pytest

from devsec.utils.errors import (
    ApiError,
    AuthError,
    ConfigError,
    DevSecError,
    ExitCode,
    PolicyViolationError,
    ScanError,
    UsageError,
    error_detail,
)


def test_exit_code_values_are_stable():
    assert int(ExitCode.SUCCESS) == 0
    assert int(ExitCode.POLICY_VIOLATION) == 1
    assert int(ExitCode.USAGE) == 2
    assert int(ExitCode.AUTH) == 3
    assert int(ExitCode.API) == 4
    assert int(ExitCode.SCAN_FAILURE) == 5


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (UsageError("bad usage"), ExitCode.USAGE),
        (AuthError("bad token"), ExitCode.AUTH),
        (ApiError("server 500"), ExitCode.API),
        (ScanError("scan failed"), ExitCode.SCAN_FAILURE),
        (PolicyViolationError("threshold exceeded"), ExitCode.POLICY_VIOLATION),
        (ConfigError("bad config"), ExitCode.USAGE),
    ],
)
def test_error_classes_have_stable_exit_codes(exc, code):
    assert exc.exit_code == code


def test_error_str_never_leaks_hint():
    err = UsageError("msg", hint="do this")
    assert str(err) == "msg"
    assert err.hint == "do this"


def test_api_error_carries_request_context():
    err = ApiError(
        "boom",
        status_code=500,
        request_id="req-123",
        method="GET",
        url="/api/v1/scans",
    )
    assert err.status_code == 500
    assert err.request_id == "req-123"
    assert err.method == "GET"


def test_error_detail_serializes_api_error():
    err = ApiError("boom", status_code=500, request_id="req-1")
    detail = error_detail(err)
    assert detail["error"] == "api_error"
    assert detail["exit_code"] == 4
    assert detail["status_code"] == 500
    assert detail["request_id"] == "req-1"
    json.dumps(detail)  # must be JSON serializable


def test_error_detail_maps_usage():
    detail = error_detail(UsageError("nope"))
    assert detail == {"error": "usage", "message": "nope", "exit_code": 2}


def test_error_detail_handles_unexpected():
    detail = error_detail(RuntimeError("boom"))
    assert detail["error"] == "unexpected"
    assert detail["exit_code"] == 2


def test_isauth_error_is_apifailure():
    err = AuthError("denied", status_code=401, request_id="req-9")
    assert err.status_code == 401
    assert isinstance(err, DevSecError)
