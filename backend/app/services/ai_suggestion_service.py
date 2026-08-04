"""Background AI suggestion generation for completed scans."""

from __future__ import annotations

import asyncio
import inspect
import json
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.engine import get_llm_provider
from app.config import settings
from app.core.logging import get_logger
from app.db.session import get_sync_session_factory
from app.models.ai_suggestion import AISuggestion, FixType, SuggestionStatus
from app.models.finding import Finding
from app.models.scan import Scan
from app.utils.repository_scanner import RepositoryScanner

logger = get_logger(__name__)

MAX_FINDINGS_PER_BATCH = 10
MAX_FILE_CONTEXT_CHARS = 2000
AI_CALL_TIMEOUT_SECONDS = 60


@dataclass
class AISuggestionGenerationResult:
    """Summary of a background AI suggestion run."""

    findings_processed: int
    findings_updated: int
    suggestions_upserted: int


def schedule_ai_suggestions_generation(scan_id: UUID | str) -> None:
    """Run AI suggestion generation in a detached worker thread."""
    scan_id_str = str(scan_id)
    worker = threading.Thread(
        target=run_ai_suggestions_generation,
        args=(scan_id_str,),
        name=f"ai-suggestions-{scan_id_str[:8]}",
        daemon=True,
    )
    worker.start()


def run_ai_suggestions_generation(scan_id: UUID | str) -> None:
    """Entry point for detached background AI suggestion generation."""
    try:
        generate_ai_suggestions_for_scan(scan_id)
    except Exception as exc:  # pragma: no cover - best effort background logging
        logger.exception(
            "Background AI suggestion generation crashed",
            scan_id=str(scan_id),
            error=str(exc),
        )


def generate_ai_suggestions_for_scan(
    scan_id: UUID | str,
    db: Session | None = None,
    service: AISuggestionGenerationService | None = None,
) -> AISuggestionGenerationResult:
    """Generate and persist AI suggestions for findings already saved in the database."""
    owns_session = db is None
    session = db or get_sync_session_factory()()
    generator = service or AISuggestionGenerationService()

    try:
        return generator.generate_for_scan(session, scan_id)
    finally:
        if owns_session:
            session.close()


class AISuggestionGenerationService:
    """Generate AI suggestions for stored findings with bounded batch requests."""

    def __init__(
        self,
        llm_provider: Any | None = None,
        repo_scanner: RepositoryScanner | None = None,
        batch_size: int | None = None,
        max_file_chars: int | None = None,
        call_timeout_seconds: int | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.repo_scanner = repo_scanner or RepositoryScanner()
        self.batch_size = batch_size or int(
            getattr(settings, "AI_SUGGESTION_BATCH_SIZE", None) or MAX_FINDINGS_PER_BATCH
        )
        self.max_file_chars = max_file_chars or int(
            getattr(settings, "AI_SUGGESTION_MAX_FILE_CHARS", None) or MAX_FILE_CONTEXT_CHARS
        )
        self.call_timeout_seconds = call_timeout_seconds or int(
            getattr(settings, "AI_CALL_TIMEOUT_SECONDS", None) or AI_CALL_TIMEOUT_SECONDS
        )
        self.progress_store = None
        self.scan_progress_manager = None

    def generate_for_scan(
        self,
        db: Session,
        scan_id: UUID | str,
    ) -> AISuggestionGenerationResult:
        """Generate AI suggestions for a completed scan."""
        scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
        scan = db.get(Scan, scan_uuid)
        if not scan:
            raise ValueError(f"Scan not found: {scan_id}")

        if scan.ai_status == "completed":
            findings_count = db.scalar(
                select(func.count()).select_from(Finding).where(Finding.scan_id == scan_uuid)
            )
            return AISuggestionGenerationResult(
                findings_processed=findings_count or 0,
                findings_updated=0,
                suggestions_upserted=0,
            )

        findings = db.execute(
            select(Finding)
            .where(Finding.scan_id == scan_uuid)
            .order_by(Finding.created_at.asc())
        ).scalars().all()

        scan.ai_status = "processing"
        scan.ai_error_message = None
        scan.ai_completed_at = None
        db.commit()

        if not findings:
            scan.ai_status = "completed"
            scan.ai_completed_at = datetime.utcnow()
            db.commit()
            return AISuggestionGenerationResult(
                findings_processed=0,
                findings_updated=0,
                suggestions_upserted=0,
            )

        repo_path: str | None = None
        file_snippets: dict[str, str] = {}
        ai_capable = self._supports_prompt_generation()

        try:
            if ai_capable:
                repo_path, _ = self.repo_scanner.clone_repository(
                    scan.repository_url,
                    scan.branch,
                    scan.commit_hash,
                    settings.GITHUB_TOKEN,
                )
                file_snippets = self._load_file_snippets(Path(repo_path), findings)

            findings_updated = 0
            total_findings = len(findings)
            batches = list(_batched(findings, self.batch_size))

            # Initialize progress store for AI progress
            try:
                from app.services.scan_progress_store import scan_progress_store
                self.progress_store = scan_progress_store
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.progress_store.add_log(str(scan_uuid), f"Generating AI recommendations for {total_findings} findings...")
                )
                loop.close()
            except Exception:
                pass

            for batch_idx, batch in enumerate(batches):
                batch_results = asyncio.run(
                    self._generate_batch_results(batch, file_snippets, ai_capable)
                )
                findings_updated += self._apply_batch_results(db, batch, batch_results)
                db.commit()

                # Update progress after each batch
                try:
                    from app.services.scan_progress_store import scan_progress_store
                    from app.websockets.scan_progress import scan_progress_manager
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        scan_progress_store.add_log(
                            str(scan_uuid),
                            f"AI recommendations {batch_idx * self.batch_size + len(batch)} of {total_findings}",
                        )
                    )
                    loop.run_until_complete(
                        scan_progress_manager.broadcast_log(
                            str(scan_uuid),
                            f"AI recommendation {batch_idx * self.batch_size + len(batch)} of {total_findings}",
                        )
                    )
                    loop.run_until_complete(
                        scan_progress_manager.broadcast_progress(
                            scan_id=str(scan_uuid),
                            progress=100,
                            status="completed",
                            current_step=f"AI: {batch_idx * self.batch_size + len(batch)}/{total_findings}",
                        )
                    )
                    loop.close()
                except Exception:
                    pass

            suggestions_upserted = self._upsert_ai_suggestions(db, scan_uuid, findings)

            scan.ai_status = "completed"
            scan.ai_completed_at = datetime.utcnow()
            scan.ai_error_message = None
            db.commit()

            # Broadcast AI completion
            try:
                from app.websockets.scan_progress import (
                    scan_progress_manager,
                )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    scan_progress_manager.broadcast_log(str(scan_uuid), "AI recommendation generation completed")
                )
                loop.run_until_complete(
                    self.progress_store.add_log(str(scan_uuid), "AI suggestions generated successfully")
                )
                # Send AI completion event
                loop.run_until_complete(
                    scan_progress_manager.broadcast_ai_completed(
                        str(scan_uuid),
                        status="completed",
                        suggestions_count=suggestions_upserted,
                    )
                )
                loop.close()
            except Exception:
                pass

            logger.info(
                "AI suggestion generation complete",
                scan_id=str(scan_uuid),
                findings_processed=len(findings),
                findings_updated=findings_updated,
                suggestions_upserted=suggestions_upserted,
                used_llm=ai_capable,
            )

            return AISuggestionGenerationResult(
                findings_processed=len(findings),
                findings_updated=findings_updated,
                suggestions_upserted=suggestions_upserted,
            )
        except Exception as exc:
            db.rollback()
            scan = db.get(Scan, scan_uuid)
            if scan:
                scan.ai_status = "failed"
                scan.ai_error_message = str(exc)[:1000]
                db.commit()
            raise
        finally:
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

    async def _generate_batch_results(
        self,
        findings: Sequence[Finding],
        file_snippets: dict[str, str],
        ai_capable: bool,
    ) -> list[dict[str, Any]]:
        """Generate AI payload for one findings batch."""
        if not ai_capable:
            return [self._build_fallback_result(finding) for finding in findings]

        prompt = self._build_batch_prompt(findings, file_snippets)

        try:
            raw_response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.call_timeout_seconds,
            )
            parsed = self._parse_batch_response(raw_response)
        except Exception as exc:
            error_msg = str(exc) or type(exc).__name__
            logger.warning(
                "AI batch generation failed, using fallback suggestions",
                error=error_msg,
                findings=len(findings),
            )
            parsed = []

        results_by_id = {
            str(item.get("finding_id")): item
            for item in parsed
            if item.get("finding_id")
        }

        merged_results: list[dict[str, Any]] = []
        for finding in findings:
            result = results_by_id.get(str(finding.id), self._build_fallback_result(finding))
            result.setdefault("finding_id", str(finding.id))
            result.setdefault("ai_generated", bool(results_by_id.get(str(finding.id))))
            merged_results.append(result)

        return merged_results

    async def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider and normalize sync/async providers."""
        provider = self._get_llm_provider()
        generate = getattr(provider, "generate", None)
        if generate is None:
            raise RuntimeError("Configured LLM provider does not support raw prompt generation")

        result = generate(prompt)
        if inspect.isawaitable(result):
            return await result
        return str(result)

    def _get_llm_provider(self) -> Any:
        if self.llm_provider is None:
            self.llm_provider = get_llm_provider()
        return self.llm_provider

    def _supports_prompt_generation(self) -> bool:
        provider = self._get_llm_provider()
        if provider.__class__.__name__ == "MockLLMProvider":
            return False
        return callable(getattr(provider, "generate", None))

    def _build_batch_prompt(
        self,
        findings: Sequence[Finding],
        file_snippets: dict[str, str],
    ) -> str:
        payload = []
        for finding in findings:
            payload.append(
                {
                    "finding_id": str(finding.id),
                    "rule_id": finding.rule_id,
                    "title": finding.rule_name,
                    "severity": finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity),
                    "category": finding.category.value if hasattr(finding.category, "value") else str(finding.category),
                    "description": finding.description,
                    "recommendation": finding.recommendation,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "file_content": file_snippets.get(str(finding.id), ""),
                }
            )

        return (
            "You are DevArchAI generating production-grade remediation guidance for infrastructure scan findings.\n"
            "Return ONLY valid JSON. The response must be a JSON array with one object per finding.\n"
            "Each object must contain: finding_id, summary, risk, impact, ai_explanation, "
            "fix_code, fix_example, full_example, best_practices, confidence, documentation_url.\n"
            "Rules:\n"
            "- Preserve the original finding_id exactly.\n"
            "- Keep summary to one sentence.\n"
            "- Use best_practices as an array of at most 3 strings.\n"
            "- confidence must be a float between 0 and 1.\n"
            "- If no code fix is appropriate, use an empty string for fix_code/fix_example/full_example.\n"
            "- documentation_url must be an empty string when you are not confident in an official source.\n"
            f"- This batch contains {len(payload)} findings.\n"
            f"Findings:\n{json.dumps(payload, ensure_ascii=True)}"
        )

    def _load_file_snippets(self, repo_root: Path, findings: Sequence[Finding]) -> dict[str, str]:
        snippets: dict[str, str] = {}
        cache: dict[str, str] = {}

        for finding in findings:
            file_path = finding.file_path or ""
            if file_path not in cache:
                cache[file_path] = self._read_file_snippet(repo_root, file_path)
            snippets[str(finding.id)] = cache[file_path]

        return snippets

    def _read_file_snippet(self, repo_root: Path, file_path: str) -> str:
        resolved_path = self._resolve_repo_file(repo_root, file_path)
        if not resolved_path or not resolved_path.is_file():
            return ""

        try:
            return resolved_path.read_text(encoding="utf-8", errors="ignore")[: self.max_file_chars]
        except Exception as exc:
            logger.warning(
                "Failed to read file snippet for AI suggestions",
                file_path=file_path,
                error=str(exc),
            )
            return ""

    def _resolve_repo_file(self, repo_root: Path, file_path: str) -> Path | None:
        if not file_path:
            return None

        normalized = file_path.replace("\\", "/")
        if "/tmp/devarchai/" in normalized:
            normalized = normalized.split("/tmp/devarchai/", 1)[1]
            normalized = normalized.split("/", 1)[1] if "/" in normalized else ""

        relative_path = normalized.strip("/")
        if not relative_path:
            return None

        resolved_path = (repo_root / relative_path).resolve()
        try:
            resolved_path.relative_to(repo_root.resolve())
        except ValueError:
            return None
        return resolved_path

    def _parse_batch_response(self, raw_response: str) -> list[dict[str, Any]]:
        payload = _extract_json_payload(raw_response)
        parsed = json.loads(payload)

        if isinstance(parsed, dict):
            parsed = parsed.get("findings") or parsed.get("results") or []

        if not isinstance(parsed, list):
            raise ValueError("AI response must be a JSON array")

        return [item for item in parsed if isinstance(item, dict)]

    def _apply_batch_results(
        self,
        db: Session,
        findings: Sequence[Finding],
        results: Sequence[dict[str, Any]],
    ) -> int:
        results_by_id = {str(result.get("finding_id")): result for result in results}
        updated = 0

        for finding in findings:
            result = results_by_id.get(str(finding.id))
            if not result:
                continue

            best_practices = result.get("best_practices")
            if isinstance(best_practices, str):
                best_practices = [best_practices]
            if not isinstance(best_practices, list):
                best_practices = []

            finding.summary = _clean_text(result.get("summary")) or finding.summary
            finding.risk = _clean_text(result.get("risk")) or finding.risk
            finding.impact = _clean_text(result.get("impact")) or finding.impact
            finding.ai_explanation = _clean_text(result.get("ai_explanation")) or finding.ai_explanation
            finding.fix_code = _clean_text(result.get("fix_code")) or finding.fix_code
            finding.fix_example = _clean_text(result.get("fix_example")) or finding.fix_example
            finding.full_example = _clean_text(result.get("full_example")) or finding.full_example
            finding.best_practices = json.dumps([str(item) for item in best_practices[:3]]) if best_practices else finding.best_practices
            finding.documentation_url = _clean_text(result.get("documentation_url")) or finding.documentation_url
            confidence = _coerce_confidence(result.get("confidence"))
            finding.confidence = confidence
            finding.confidence_score = confidence
            finding.ai_generated = bool(result.get("ai_generated"))
            db.add(finding)
            updated += 1

        return updated

    def _upsert_ai_suggestions(
        self,
        db: Session,
        scan_id: UUID,
        findings: Sequence[Finding],
    ) -> int:
        existing = db.execute(
            select(AISuggestion).where(AISuggestion.scan_id == scan_id)
        ).scalars().all()
        suggestions_by_finding_id = {str(item.finding_id): item for item in existing}
        upserted = 0

        for finding in findings:
            fix_type = self._determine_fix_type(finding)
            metadata = {
                "rule_id": finding.rule_id,
                "recommendation": finding.recommendation,
                "best_practices": self._deserialize_best_practices(finding.best_practices),
                "ai_generated": finding.ai_generated,
            }

            suggestion = suggestions_by_finding_id.get(str(finding.id))
            if suggestion is None:
                suggestion = AISuggestion(
                    finding_id=finding.id,
                    scan_id=scan_id,
                )
                db.add(suggestion)

            suggestion.title = finding.summary or finding.rule_name or f"Fix {finding.rule_id}"
            suggestion.description = finding.ai_explanation or finding.description or ""
            suggestion.severity = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
            suggestion.confidence = _coerce_confidence(finding.confidence or finding.confidence_score)
            suggestion.category = finding.category.value if hasattr(finding.category, "value") else str(finding.category)
            suggestion.fix_type = fix_type
            suggestion.file_path = finding.file_path or ""
            suggestion.line_number = finding.line_number
            suggestion.fix_code = finding.fix_code or finding.fix_example or finding.full_example
            suggestion.auto_fix_available = bool(suggestion.fix_code)
            suggestion.status = SuggestionStatus.OPEN
            suggestion.additional_data = json.dumps(metadata) if metadata else None
            upserted += 1

        return upserted

    def _determine_fix_type(self, finding: Finding) -> FixType:
        path_lower = (finding.file_path or "").lower()
        if ".tf" in path_lower or "terraform" in path_lower:
            return FixType.TERRAFORM
        if "dockerfile" in path_lower or "docker" in path_lower:
            return FixType.DOCKERFILE
        if "kubernetes" in path_lower or "k8s" in path_lower or path_lower.endswith((".yaml", ".yml")):
            return FixType.KUBERNETES
        if ".github" in path_lower or "jenkins" in path_lower or "gitlab-ci" in path_lower or "pipeline" in path_lower:
            return FixType.CI_CD
        return FixType.GENERAL

    def _deserialize_best_practices(self, raw_best_practices: str | None) -> list[str]:
        if not raw_best_practices:
            return []
        try:
            parsed = json.loads(raw_best_practices)
        except json.JSONDecodeError:
            return [raw_best_practices]
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def _build_fallback_result(self, finding: Finding) -> dict[str, Any]:
        best_practices = self._deserialize_best_practices(finding.best_practices)
        return {
            "finding_id": str(finding.id),
            "summary": finding.summary or f"{finding.rule_name}: {finding.recommendation}",
            "risk": finding.risk or finding.description,
            "impact": finding.impact or finding.recommendation,
            "ai_explanation": finding.ai_explanation or finding.description,
            "fix_code": finding.fix_code or "",
            "fix_example": finding.fix_example or finding.fix_code or "",
            "full_example": finding.full_example or "",
            "best_practices": best_practices or [finding.recommendation],
            "confidence": _coerce_confidence(finding.confidence or finding.confidence_score or 0.55),
            "documentation_url": finding.documentation_url or "",
            "ai_generated": False,
        }


def _batched(items: Sequence[Any], batch_size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def _extract_json_payload(raw_response: str) -> str:
    stripped = raw_response.strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 2:
            stripped = parts[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()

    starts = [index for index in (stripped.find("["), stripped.find("{")) if index != -1]
    if not starts:
        raise ValueError("No JSON payload found in AI response")

    start_index = min(starts)
    end_index = max(stripped.rfind("]"), stripped.rfind("}"))
    if end_index < start_index:
        raise ValueError("Malformed JSON payload in AI response")

    return stripped[start_index : end_index + 1]


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.55
    return max(0.0, min(confidence, 1.0))
