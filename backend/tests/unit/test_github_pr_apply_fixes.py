"""Tests for GitHubPRService.apply_fixes grouping and preservation."""

import tempfile
from pathlib import Path

import pytest

from app.services.github_pr import GitHubPRService


GO_DOCKERFILE = """FROM golang:1.22 AS builder
WORKDIR /app
RUN go build -o /out/server .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /out/server /server
ENTRYPOINT ["/server"]
"""

NODE_DOCKERFILE = """FROM node:20-alpine
CMD ["npm", "start"]
"""


@pytest.fixture
def cloned_repo(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(GO_DOCKERFILE, encoding="utf-8")
    return tmp_path


class TestApplyFixesSafe:
    def test_rejects_unsafe_full_file_fix(self, cloned_repo):
        service = GitHubPRService(
            github_token="ghs_testtoken1234567890",
            repo_url="https://github.com/example/acme.git",
        )
        service.temp_dir = str(cloned_repo)
        service.repo_name = "acme"

        modified = service.apply_fixes(
            [
                {
                    "file_path": "Dockerfile",
                    "fix_code": NODE_DOCKERFILE,
                    "finding_id": "finding-1",
                }
            ],
            atomic_mode=False,
            selected_finding_ids=["finding-1"],
        )
        assert modified == []
        assert (cloned_repo / "Dockerfile").read_text(encoding="utf-8") == GO_DOCKERFILE

    def test_applies_unified_diff_fix(self, cloned_repo):
        from app.services.remediation_patch import build_unified_diff

        updated = GO_DOCKERFILE + "\nUSER 65532:65532\n"
        diff = build_unified_diff("Dockerfile", GO_DOCKERFILE, updated)

        service = GitHubPRService(
            github_token="ghs_testtoken1234567890",
            repo_url="https://github.com/example/acme.git",
        )
        service.temp_dir = str(cloned_repo)
        service.repo_name = "acme"

        modified = service.apply_fixes(
            [
                {
                    "file_path": "Dockerfile",
                    "unified_diff": diff,
                    "finding_id": "finding-1",
                }
            ]
        )

        assert modified == ["Dockerfile"]
        content = (cloned_repo / "Dockerfile").read_text(encoding="utf-8")
        assert "USER 65532:65532" in content
        assert "golang:1.22" in content
