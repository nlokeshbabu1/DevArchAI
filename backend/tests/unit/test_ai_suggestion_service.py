"""Unit tests for background AI suggestion generation helpers."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from app.models.finding import Category, Finding, Severity
from app.services.ai_suggestion_service import (
    MAX_FILE_CONTEXT_CHARS,
    AISuggestionGenerationService,
    _batched,
    _extract_json_payload,
)


def _finding() -> Finding:
    return Finding(
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


class _FailingProvider:
    """LLM provider whose generate() always raises (e.g. missing package)."""

    async def generate(self, prompt: str) -> str:
        raise RuntimeError("The 'gpt4all' package is not installed")


class _WorkingProvider:
    """LLM provider that returns a valid JSON batch response."""

    async def generate(self, prompt: str) -> str:
        findings = []
        for finding in _FINDINGS:
            findings.append(
                {
                    "finding_id": str(finding.id),
                    "summary": "AI summary",
                    "risk": "AI risk",
                    "impact": "AI impact",
                    "ai_explanation": "AI explanation",
                    "fix_code": "# fix",
                    "fix_example": "# example",
                    "full_example": "# full",
                    "best_practices": ["bp1"],
                    "confidence": 0.9,
                    "documentation_url": "",
                }
            )
        return json.dumps(findings)


_FINDINGS = [_finding(), _finding()]


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

    finding = _finding()
    finding.file_path = "/tmp/devarchai/hash_repo/terraform/main.tf"

    service = AISuggestionGenerationService(
        llm_provider=object(), max_file_chars=MAX_FILE_CONTEXT_CHARS
    )
    snippets = service._load_file_snippets(repo_root, [finding])

    assert len(snippets[str(finding.id)]) == MAX_FILE_CONTEXT_CHARS
    assert snippets[str(finding.id)] == "a" * MAX_FILE_CONTEXT_CHARS


def test_batch_llm_failure_uses_fallbacks_and_reports_no_llm():
    service = AISuggestionGenerationService(llm_provider=_FailingProvider())

    results, llm_used = asyncio.run(
        service._generate_batch_results(_FINDINGS, {}, ai_capable=True)
    )

    assert llm_used is False
    assert len(results) == len(_FINDINGS)
    assert all(result["ai_generated"] is False for result in results)
    assert all(result["summary"] for result in results)


def test_batch_llm_success_reports_llm_used():
    service = AISuggestionGenerationService(llm_provider=_WorkingProvider())

    results, llm_used = asyncio.run(
        service._generate_batch_results(_FINDINGS, {}, ai_capable=True)
    )

    assert llm_used is True
    assert len(results) == len(_FINDINGS)
    assert all(result["ai_generated"] is True for result in results)
    assert all(result["summary"] == "AI summary" for result in results)


def test_batch_not_ai_capable_reports_no_llm():
    service = AISuggestionGenerationService(llm_provider=_WorkingProvider())

    results, llm_used = asyncio.run(
        service._generate_batch_results(_FINDINGS, {}, ai_capable=False)
    )

    assert llm_used is False
    assert all(result["ai_generated"] is False for result in results)


def test_supports_prompt_generation_mock_is_not_capable(monkeypatch):
    from app.ai.engine import MockLLMProvider

    service = AISuggestionGenerationService(llm_provider=MockLLMProvider())
    assert service._supports_prompt_generation() is False


def test_supports_prompt_generation_gpt4all_missing_package_is_not_capable(monkeypatch):
    class GPT4AllProvider:
        def generate(self, prompt: str) -> str:
            return ""

    service = AISuggestionGenerationService(llm_provider=GPT4AllProvider())
    monkeypatch.setattr(
        "app.services.ai_suggestion_service.logger", _NullLogger()
    )
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "gpt4all":
            raise ImportError("No module named 'gpt4all'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert service._supports_prompt_generation() is False


class _NullLogger:
    def warning(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

