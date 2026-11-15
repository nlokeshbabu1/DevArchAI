"""Regression: scan results must not lazy-load relationships in async context."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus

from tests.integration.guest_session import guest_session_headers

BUCKETS = {"critical", "high", "medium", "low", "info"}


@pytest.mark.asyncio
async def test_scan_results_with_linked_repository_no_lazy_load(client, test_db):
    """Scans linked to a repository must return 200 without MissingGreenlet."""
    repo_id = uuid4()
    scan_id = uuid4()
    repo = Repository(
        id=repo_id,
        name="nlokeshbabu1/Terraform",
        url="https://github.com/nlokeshbabu1/Terraform",
        default_branch="master",
    )
    scan = Scan(
        id=scan_id,
        repository_id=repo_id,
        repository_url=repo.url,
        branch="master",
        status=ScanStatus.COMPLETED,
        overall_score=88.0,
        detected_stack={"terraform_files": ["main.tf"]},
    )
    test_db.add(repo)
    test_db.add(scan)
    await test_db.commit()

    headers = await guest_session_headers(test_db, scan_id)
    response = await client.get(f"/api/v1/scan/results/{scan_id}", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["scan_id"] == str(scan_id)
    assert data["repository_name"] == "nlokeshbabu1/Terraform"
    assert set(data["severity_counts"].keys()) == BUCKETS
    assert data["repository_size"] is None
