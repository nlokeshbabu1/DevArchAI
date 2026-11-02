"""PR flow must reuse stored patches without invoking patch LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.remediation_patch import build_unified_diff
from app.services.remediation_workflow import RemediationWorkflow

GO = "FROM golang:1.22\nCMD [\"/app\"]\n"


class FakeSeverity:
    value = "high"


class FakeFinding:
    id = "f-1"
    rule_id = "r1"
    rule_name = "n"
    severity = FakeSeverity()
    description = "d"
    recommendation = "r"
    file_path = "Dockerfile"
    line_number = 1
    fix_code = None
    fix_example = None
    evidence = None
    processing_metadata = None

    def __init__(self, metadata: dict):
        import json

        self.processing_metadata = json.dumps(metadata)


@pytest.mark.asyncio
async def test_pr_plan_does_not_call_patch_llm_when_stored_diff(mini_repo_git):
    from git import Repo

    head = Repo(str(mini_repo_git)).head.commit.hexsha
    content_hash = __import__(
        "app.services.remediation_patch", fromlist=["file_content_hash"]
    ).file_content_hash(GO)
    diff = build_unified_diff("Dockerfile", GO, GO + "USER 65532\n")
    finding = FakeFinding(
        {
            "remediation": {
                "patch_status": "validation_passed",
                "unified_diff": diff,
                "original_content_sha256": content_hash,
                "commit_sha": head,
            }
        }
    )

    with patch(
        "app.services.remediation_workflow.generate_unified_diff_patch",
        new=AsyncMock(side_effect=AssertionError("PR must not call patch LLM")),
    ):
        workflow = RemediationWorkflow()
        plan = await workflow.build_plan_from_clone(
            str(mini_repo_git),
            "repo",
            [finding],
            branch="main",
            scan_commit_hash=head,
            atomic_mode=True,
            generate_missing_patches=False,
        )

    assert plan.fixes
    assert plan.fixes[0].get("unified_diff")


@pytest.fixture
def mini_repo_git(tmp_path):
    (tmp_path / "Dockerfile").write_text(GO, encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path
