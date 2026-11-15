"""Tests for scan-time remediation patch generation and metadata persistence."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.finding_normalizer import parse_processing_metadata
from app.services.remediation_metadata import (
    PatchGenerationStatus,
    merge_remediation_metadata,
    patch_is_reusable,
    remediation_idempotency_key,
)
from app.services.remediation_patch import build_unified_diff
from app.services.remediation_scan_service import (
    generate_scan_time_patch_for_finding,
    persist_remediation_on_finding,
)

GO = """FROM golang:1.22
WORKDIR /app
RUN go build -o /app/server .
CMD ["/app/server"]
"""


class FakeScan:
    repository_url = "https://github.com/org/repo"
    branch = "main"
    commit_hash = "abc123def"
    detected_stack = {"detected_stack": ["docker"]}


class FakeFinding:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "f-1")
        self.rule_id = kwargs.get("rule_id", "rule-1")
        self.rule_name = "Test rule"
        self.severity = type("S", (), {"value": "high"})()
        self.description = "Issue"
        self.recommendation = "Fix it"
        self.file_path = kwargs.get("file_path", "Dockerfile")
        self.line_number = 10
        self.processing_metadata = kwargs.get("processing_metadata")
        self.evidence = None


class FakeLoader:
    def read_full_file(self, scan, finding, max_chars=48000):
        return GO, "Dockerfile"


@pytest.mark.asyncio
async def test_scan_patch_persists_metadata_and_preserves_other_keys():
    finding = FakeFinding()
    updated = GO + "\nUSER 65532\n"
    diff = build_unified_diff("Dockerfile", GO, updated)

    with patch(
        "app.services.remediation_scan_service.generate_unified_diff_patch",
        new=AsyncMock(
            return_value={
                "status": "ready",
                "unified_diff": diff,
                "explanation": "Add non-root user",
                "assumptions": [],
                "breaking_changes": [],
                "required_validations": ["preservation"],
                "confidence": 0.9,
            }
        ),
    ):
        block = await generate_scan_time_patch_for_finding(
            scan=FakeScan(),
            finding=finding,
            file_loader=FakeLoader(),
            job_id="job-1",
        )

    assert block["patch_status"] == PatchGenerationStatus.VALIDATION_PASSED.value
    assert block["unified_diff"]

    class Session:
        def add(self, _):
            pass

    finding.processing_metadata = json.dumps({"detection_source": "rule_engine"})
    await persist_remediation_on_finding(Session(), finding, block)
    meta = parse_processing_metadata(finding.processing_metadata)
    assert meta.get("detection_source") == "rule_engine"
    assert meta["remediation"]["unified_diff"]


@pytest.mark.asyncio
async def test_idempotency_skips_second_generation():
    key = remediation_idempotency_key(
        finding_id="f-1",
        commit_sha="abc123def",
        file_path="Dockerfile",
        rule_id="rule-1",
        line_number=10,
    )
    prior = {
        "idempotency_key": key,
        "patch_status": PatchGenerationStatus.VALIDATION_PASSED.value,
        "unified_diff": "---",
        "commit_sha": "abc123def",
    }
    finding = FakeFinding(
        processing_metadata=json.dumps({"remediation": prior}),
    )

    with patch(
        "app.services.remediation_scan_service.generate_unified_diff_patch",
        new=AsyncMock(side_effect=AssertionError("should not call LLM")),
    ):
        block = await generate_scan_time_patch_for_finding(
            scan=FakeScan(),
            finding=finding,
            file_loader=FakeLoader(),
        )
    assert block["patch_status"] == PatchGenerationStatus.VALIDATION_PASSED.value


def test_patch_is_reusable_requires_matching_hash():
    rem = {
        "patch_status": "validation_passed",
        "unified_diff": "x",
        "commit_sha": "abc",
        "original_content_sha256": "hash1",
    }
    assert patch_is_reusable(rem, commit_sha="abc", file_content_hash="hash1")
    assert not patch_is_reusable(rem, commit_sha="abc", file_content_hash="hash2")


def test_merge_remediation_metadata_preserves_sibling_keys():
    raw = json.dumps({"detection_source": "external_scanner", "remediation": {"patch_status": "pending"}})
    merged = merge_remediation_metadata(
        raw,
        {"patch_status": "validation_passed", "unified_diff": "---"},
    )
    meta = json.loads(merged)
    assert meta["detection_source"] == "external_scanner"
    assert meta["remediation"]["unified_diff"] == "---"
