"""Abstract base for knowledge providers and the KnowledgeDocument data model.

Every knowledge provider returns a list of KnowledgeDocument objects.
The recommendation engine consumes these documents as context for the LLM prompt.
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeDocument:
    """A single retrieved knowledge artifact.

    Attributes:
        source: Provider name that produced this document (e.g. "aws_docs").
        title: Human-readable title.
        content: The actual knowledge text (markdown or plain text).
        url: Canonical URL for the source document.
        version: Document or API version string (e.g. "2024-07-01").
        retrieved_at: When this document was fetched (UTC).
        relevance_score: 0.0–1.0 relevance to the query.
        metadata: Extra provider-specific key-value pairs.
    """

    source: str
    title: str
    content: str
    url: str = ""
    version: str = ""
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    relevance_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cache_key(self) -> str:
        """Deterministic cache key based on source + title."""
        raw = f"{self.source}:{self.title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def to_prompt_context(self) -> str:
        """Serialize to a string suitable for LLM prompt injection."""
        parts = [f"## {self.title} (source: {self.source})"]
        if self.url:
            parts.append(f"Reference: {self.url}")
        if self.version:
            parts.append(f"Version: {self.version}")
        parts.append(self.content)
        return "\n\n".join(parts)


class KnowledgeProvider(abc.ABC):
    """Abstract base for all knowledge retrieval providers.

    Subclasses must implement `name` and `retrieve`.
    The registry manages lifecycle and caching.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'aws_docs', 'aws_pricing')."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this provider retrieves."""
        return ""

    @abc.abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        """Retrieve knowledge documents matching the query.

        Args:
            query: Natural language query describing the knowledge needed.
            service: AWS service name to scope results (e.g. "ec2", "s3").
            region: AWS region for pricing or region-specific guidance.
            max_results: Maximum documents to return.

        Returns:
            List of KnowledgeDocument, sorted by relevance descending.
        """
        ...

    async def health_check(self) -> bool:
        """Return True if the provider is reachable and configured."""
        return True
