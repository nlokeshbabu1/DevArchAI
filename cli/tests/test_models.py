"""Tests for Pydantic models and API response parsing."""

from __future__ import annotations

from devsec.models.detection import DetectedStack
from devsec.models.git import GitMetadata
from devsec.models.project import Project, ProjectList


def test_project_model_tolerates_extra_fields():
    payload = {
        "id": "abc",
        "user_id": "u1",
        "name": "acme/infra",
        "url": "https://github.com/acme/infra",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
    }
    project = Project.model_validate(payload)
    assert project.id == "abc"
    assert project.name == "acme/infra"


def test_project_defaults():
    project = Project(
        id="abc",
        name="n",
        url="https://github.com/a/b",
    )
    assert project.default_branch == "main"
    assert project.issues == {}
    assert project.scan_status is None


def test_project_list_from_response():
    payload = {
        "repositories": [
            {
                "id": "abc",
                "name": "n",
                "url": "https://github.com/a/b",
                "scan_status": "completed",
                "issues": {"high": 3},
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    listing = ProjectList.from_response(payload)
    assert listing.total == 1
    assert listing.projects[0].scan_status == "completed"
    assert listing.projects[0].issues["high"] == 3


def test_detected_stack_technologies_property():
    stack = DetectedStack(has_docker=True, has_terraform=True)
    assert set(stack.technologies) == {"docker", "terraform"}
    assert stack.summary() == "docker, terraform"


def test_detected_stack_empty_summary():
    assert DetectedStack().summary() == "No supported technologies detected"


def test_detected_stack_to_backend_dict():
    stack = DetectedStack(has_helm=True, helm_files=["Chart.yaml"], languages=["go"])
    payload = stack.to_backend_dict()
    assert payload["has_helm"] is True
    assert "languages" not in payload
    assert "has_kubernetes" in payload


def test_git_metadata_require_remote_no_remote():
    meta = GitMetadata(is_git=True, root="/tmp/x")
    try:
        meta.require_remote()
    except Exception as exc:
        assert "No git remote" in str(exc)
    else:
        raise AssertionError("expected error")


def test_git_metadata_require_remote_not_git():
    meta = GitMetadata(is_git=False)
    try:
        meta.require_remote()
    except Exception as exc:
        assert "Not a git repository" in str(exc)
    else:
        raise AssertionError("expected error")


def test_git_metadata_display_name_from_url():
    meta = GitMetadata(remote_url="https://github.com/acme/infra.git")
    assert meta.display_name == "acme/infra"


def test_user_info_parses():
    from devsec.models.project import Project
    from devsec.models.user import UserInfo

    project = Project.model_validate(
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "name": "acme/infra",
            "url": "https://github.com/acme/infra",
            "default_branch": "main",
            "created_at": "2026-01-15T08:30:00Z",
        }
    )
    assert project.provider == "GitHub"
    assert project.repository == "acme/infra"
    assert project.created_at is not None

    # UUID-like ids coerce to str.
    project_uuid = Project.model_validate(
        {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "name": "x",
            "url": "https://gitlab.com/x/y",
        }
    )
    assert project_uuid.provider == "GitLab"
    assert isinstance(project_uuid.id, str)

    user = UserInfo.model_validate(
        {"id": "1", "email": "a@b.c", "username": "u", "extra": "ignored"}
    )
    assert user.email == "a@b.c"
