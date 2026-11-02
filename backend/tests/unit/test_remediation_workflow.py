"""Tests for universal remediation workflow (no live LLM / GitHub)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.services.remediation_discovery import discover_repository
from app.services.remediation_patch import build_unified_diff
from app.services.remediation_workflow import RemediationWorkflow


GO_DOCKERFILE = """FROM golang:1.22 AS builder
WORKDIR /app
RUN go build -o /out/server .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /out/server /server
ENTRYPOINT ["/server"]
"""


@dataclass
class FakeFinding:
    id: str
    rule_id: str
    rule_name: str
    severity: object
    description: str
    recommendation: str
    file_path: str
    line_number: int | None = None
    fix_code: str | None = None
    fix_example: str | None = None
    processing_metadata: dict | None = None
    evidence: str | None = None


class FakeSeverity:
    value = "high"


@pytest.fixture
def mini_repo(tmp_path):
    (tmp_path / "Dockerfile").write_text(GO_DOCKERFILE, encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/app\n\ngo 1.22\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=test@test.com", "-c", "user.name=test", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.mark.asyncio
async def test_discovery_from_clone(mini_repo):
    disc = discover_repository(str(mini_repo), commit_sha="abc123", branch="main")
    assert "go_modules" in disc.package_managers
    assert disc.stack is not None
    assert disc.stack.has_docker is True


@pytest.mark.asyncio
async def test_workflow_applies_stored_unified_diff(mini_repo):
    updated = GO_DOCKERFILE + "\nUSER 65532:65532\n"
    diff = build_unified_diff("Dockerfile", GO_DOCKERFILE, updated)
    finding = FakeFinding(
        id="f-1",
        rule_id="rule-docker-user",
        rule_name="Non-root user",
        severity=FakeSeverity(),
        description="Run as non-root",
        recommendation="Add USER directive",
        file_path="Dockerfile",
        processing_metadata={"remediation": {"unified_diff": diff}},
    )

    workflow = RemediationWorkflow()
    plan = await workflow.build_plan_from_clone(
        str(mini_repo),
        "repo",
        [finding],
        branch="main",
        scan_commit_hash="abc123",
        atomic_mode=True,
        generate_missing_patches=False,
    )

    assert plan.atomic_ok is True
    assert len(plan.fixes) == 1
    assert plan.fixes[0]["unified_diff"]


@pytest.mark.asyncio
async def test_workflow_atomic_fails_when_patch_missing(mini_repo):
    finding = FakeFinding(
        id="f-2",
        rule_id="rule-x",
        rule_name="Issue",
        severity=FakeSeverity(),
        description="Problem",
        recommendation="Fix manually",
        file_path="Dockerfile",
        fix_code="USER 65532",
    )
    workflow = RemediationWorkflow()
    plan = await workflow.build_plan_from_clone(
        str(mini_repo),
        "repo",
        [finding],
        branch="main",
        atomic_mode=True,
        generate_missing_patches=False,
    )
    assert plan.atomic_ok is False
    assert plan.fixes == []


@pytest.mark.asyncio
async def test_workflow_partial_mode_allows_subset(mini_repo):
    diff = build_unified_diff(
        "Dockerfile",
        GO_DOCKERFILE,
        GO_DOCKERFILE + "\nUSER 65532:65532\n",
    )
    good = FakeFinding(
        id="f-good",
        rule_id="r1",
        rule_name="n1",
        severity=FakeSeverity(),
        description="d",
        recommendation="r",
        file_path="Dockerfile",
        processing_metadata={"remediation": {"unified_diff": diff}},
    )
    bad = FakeFinding(
        id="f-bad",
        rule_id="r2",
        rule_name="n2",
        severity=FakeSeverity(),
        description="d",
        recommendation="r",
        file_path="missing.txt",
    )
    workflow = RemediationWorkflow()
    plan = await workflow.build_plan_from_clone(
        str(mini_repo),
        "repo",
        [good, bad],
        branch="main",
        atomic_mode=False,
        generate_missing_patches=False,
    )
    assert len(plan.fixes) == 1
    assert plan.fixes[0]["finding_id"] == "f-good"
