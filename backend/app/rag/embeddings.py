"""Embedding router for the RAG knowledge layer.

Auto-selects an embedding provider from configuration:

- ``EMBEDDING_PROVIDER=auto`` (default): use OpenAI embeddings when
  ``OPENAI_API_KEY`` is present, otherwise fall back to a local offline model.
- ``EMBEDDING_PROVIDER=openai``: always use OpenAI (requires a key).
- ``EMBEDDING_PROVIDER=local``: always use the local offline model.

The local provider lazily imports ``sentence_transformers``. If it is not
installed, local embeddings raise :class:`EmbeddingUnavailable`, and callers
fall back to keyword-based retrieval instead of failing.

Every produced vector must match ``settings.EMBEDDING_DIMENSION``; a mismatch
raises :class:`EmbeddingDimensionError` so the caller can degrade gracefully.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingUnavailable(RuntimeError):
    """Raised when no embedding provider is usable (e.g. no key, no local model)."""


class EmbeddingDimensionError(RuntimeError):
    """Raised when a provider returns vectors of the wrong dimension."""


class BaseEmbedder:
    """Abstract embedding provider."""

    name = "base"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings via the existing LangChain integration."""

    name = "openai"

    def __init__(self, model: str | None = None):
        self.model = model or settings.EMBEDDING_OPENAI_MODEL

    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        from langchain_openai import OpenAIEmbeddings

        client = OpenAIEmbeddings(
            model=self.model,
            api_key=settings.OPENAI_API_KEY,
        )
        start = time.monotonic()
        vectors = client.embed_documents(texts)
        logger.debug(
            "EMBEDDING_OPENAI_COMPLETE",
            count=len(texts),
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
        return vectors


class LocalEmbedder(BaseEmbedder):
    """Local offline embeddings via sentence-transformers (lazy import).

    ``sentence_transformers`` is intentionally an optional dependency: if it
    is not installed the embedder reports itself unavailable and callers
    degrade to keyword retrieval.
    """

    name = "local"

    def __init__(self, model: str | None = None):
        self.model = model or settings.EMBEDDING_LOCAL_MODEL
        self._client: Any | None = None
        self._load_error: str | None = None

    def _load(self) -> Any:
        if self._client is not None:
            return self._client
        if self._load_error is not None:
            raise EmbeddingUnavailable(self._load_error)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on env
            self._load_error = (
                "sentence-transformers is not installed. Install it to use local "
                "embeddings: pip install sentence-transformers"
            )
            raise EmbeddingUnavailable(self._load_error) from exc
        try:
            self._client = SentenceTransformer(self.model)
            logger.info("EMBEDDING_LOCAL_MODEL_LOADED", model=self.model)
            return self._client
        except Exception as exc:
            self._load_error = f"failed to load local embedding model {self.model}: {exc}"
            raise EmbeddingUnavailable(self._load_error) from exc

    def is_available(self) -> bool:
        if self._client is not None:
            return True
        try:
            self._load()
            return True
        except EmbeddingUnavailable:
            return False

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._load()
        start = time.monotonic()
        vectors = client.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
        )
        logger.debug(
            "EMBEDDING_LOCAL_COMPLETE",
            count=len(texts),
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
        return [list(map(float, vec)) for vec in vectors]


def _resolve_provider() -> str:
    """Resolve the effective embedding provider name."""
    configured = settings.EMBEDDING_PROVIDER
    if configured in ("openai", "local"):
        return configured
    # auto
    if settings.OPENAI_API_KEY:
        return "openai"
    return "local"


class EmbeddingRouter:
    """Routes embedding requests to the active provider with dimension checks."""

    def __init__(self) -> None:
        self._embedders: dict[str, BaseEmbedder] = {
            "openai": OpenAIEmbedder(),
            "local": LocalEmbedder(),
        }
        self._active_name: str | None = None

    @property
    def provider(self) -> str:
        if self._active_name is None:
            self._active_name = _resolve_provider()
        return self._active_name

    def is_semantic_available(self) -> bool:
        """True if the active provider can actually produce embeddings."""
        try:
            return self._embedders[self.provider].is_available()
        except KeyError:
            return False

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts through the active provider.

        Raises:
            EmbeddingUnavailable: if no usable provider exists.
            EmbeddingDimensionError: if vectors do not match the configured
                dimension (indicates a provider/model misconfiguration).
        """
        provider = self.provider
        embedder = self._embedders.get(provider)
        if embedder is None or not embedder.is_available():
            raise EmbeddingUnavailable(
                f"embedding provider '{provider}' is unavailable. "
                "Set OPENAI_API_KEY or install sentence-transformers for local embeddings."
            )

        if not texts:
            return []

        vectors = embedder.embed_texts(texts)
        for vec in vectors:
            if len(vec) != settings.EMBEDDING_DIMENSION:
                raise EmbeddingDimensionError(
                    f"embedding provider '{provider}' returned dimension "
                    f"{len(vec)} but EMBEDDING_DIMENSION is "
                    f"{settings.EMBEDDING_DIMENSION}. Update the setting to match "
                    "the active model."
                )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0]


# Singleton
_router: EmbeddingRouter | None = None


def get_embedding_router() -> EmbeddingRouter:
    """Get the global embedding router singleton."""
    global _router
    if _router is None:
        _router = EmbeddingRouter()
    return _router
