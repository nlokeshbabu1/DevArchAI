"""Lazy per-scan repository file snippet loader for the AI recommendation pipeline.

The loader clones the repository at most once per loader instance (per scan),
and caches snippets by file path. Snippet content is bounded to
``AI_SUGGESTION_MAX_FILE_CHARS`` and later scrubbed of secrets by the context
engine before it leaves the process.

Clone failures never raise — they degrade to empty snippets so the pipeline
continues with rule knowledge + live context alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class RepoFileSnippetLoader:
    """Bounded, lazy, cloned-once file snippet loader."""

    def __init__(
        self,
        repo_scanner: Any | None = None,
        max_chars: int | None = None,
    ) -> None:
        self._repo_scanner = repo_scanner
        self._max_chars = max_chars or int(
            getattr(settings, "AI_SUGGESTION_MAX_FILE_CHARS", None) or 500
        )
        self._repo_root: Path | None = None
        self._snippet_cache: dict[str, str] = {}
        self._clone_attempted = False

    def snippet_for(self, scan: Any, finding: Any) -> str:
        """Return a bounded snippet for a finding's file. Never raises."""
        try:
            include = bool(getattr(settings, "AI_RECOMMENDATIONS_INCLUDE_FILE_CONTEXT", True))
            if not include:
                return ""
            file_path = str(getattr(finding, "file_path", "") or "")
            if not file_path:
                return ""
            if file_path in self._snippet_cache:
                return self._snippet_cache[file_path]
            snippet = self._read(scan, file_path)
            self._snippet_cache[file_path] = snippet
            return snippet
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_SNIPPET_ERROR", error=str(exc))
            return ""

    def cleanup(self) -> None:
        """Release the cloned repository (if any)."""
        if self._repo_root is not None and self._repo_scanner is not None:
            try:
                self._repo_scanner.cleanup(str(self._repo_root))
            except Exception:
                pass
            self._repo_root = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_repo(self, scan: Any) -> Path | None:
        if self._repo_root is not None:
            return self._repo_root
        if self._clone_attempted:
            return None
        self._clone_attempted = True
        try:
            if self._repo_scanner is None:
                from app.utils.repository_scanner import RepositoryScanner
                self._repo_scanner = RepositoryScanner()
            repo_path, _ = self._repo_scanner.clone_repository(
                getattr(scan, "repository_url", ""),
                getattr(scan, "branch", "main") or "main",
                getattr(scan, "commit_hash", None),
                settings.GITHUB_TOKEN,
            )
            self._repo_root = Path(repo_path)
            return self._repo_root
        except Exception as exc:
            logger.warning("AI_RECOMMENDATION_CLONE_FAILED", error=str(exc)[:300])
            return None

    def _read(self, scan: Any, file_path: str) -> str:
        repo_root = self._ensure_repo(scan)
        if repo_root is None:
            return ""
        resolved = self._resolve_repo_file(repo_root, file_path)
        if resolved is None or not resolved.is_file():
            return ""
        try:
            return resolved.read_text(encoding="utf-8", errors="ignore")[: self._max_chars]
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_SNIPPET_READ_ERROR", error=str(exc))
            return ""

    def _resolve_repo_file(self, repo_root: Path, file_path: str) -> Path | None:
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
