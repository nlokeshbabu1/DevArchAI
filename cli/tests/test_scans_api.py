"""Tests for scan API client alignment with backend B-05 contract."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from devsec.api.scans import start_scan
from devsec.models.scan import ScanStartResponse


def test_start_scan_omits_branch_when_none():
    client = MagicMock()
    client.post_json.return_value = {
        "scan_id": "abc-123",
        "status": "pending",
        "repository_url": "https://github.com/org/repo",
        "branch": "main",
    }
    result = start_scan(
        client,
        repository_url="https://github.com/org/repo",
        branch=None,
    )
    assert isinstance(result, ScanStartResponse)
    client.post_json.assert_called_once()
    payload = client.post_json.call_args.kwargs.get("payload") or client.post_json.call_args[0][1]
    assert "branch" not in payload
