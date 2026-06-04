"""Unit tests for background AI suggestion generation helpers."""

from __future__ import annotations

from uuid import uuid4

from app.models.finding import Category, Finding, Severity
from app.services.ai_suggestion_service import (
    AISuggestionGenerationService,
    MAX_FILE_CONTEXT_CHARS,
    _batched,
    _extract_json_payload,
)


def test_batched_limits_requests_to_ten_findings():
    batches = list(_batched(list(range(23)), 10))

    assert [len(batch) for batch in batches] == [10, 10, 3]


def test_extract_json_payload_handles_markdown_wrapped_json():
    raw_response = """```json
    [{"finding_id": "123", "summary": "Use remote state"}]
    ```"""

    payload = _extract_json_payload(raw_response)

    assert payload == '[{"finding_id": "123", "summary": "Use remote state"}]'


def test_load_file_snippets_truncates_file_context(tmp_path):
    repo_root = tmp_path
    file_path = repo_root / "terraform" / "main.tf"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("a" * (MAX_FILE_CONTEXT_CHARS + 250), encoding="utf-8")

    finding = Finding(
        id=uuid4(),
        scan_id=uuid4(),
        rule_id="TF-STATE-001",
        rule_name="Remote Backend Required",
        severity=Severity.HIGH,
        category=Category.RELIABILITY,
        description="Terraform state is local",
        recommendation="Use a remote backend",
        file_path="/tmp/devarchai/hash_repo/terraform/main.tf",
    )

    service = AISuggestionGenerationService(llm_provider=object())
    snippets = service._load_file_snippets(repo_root, [finding])

    assert len(snippets[str(finding.id)]) == MAX_FILE_CONTEXT_CHARS
    assert snippets[str(finding.id)] == "a" * MAX_FILE_CONTEXT_CHARS
