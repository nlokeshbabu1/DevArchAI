"""Low-level helpers for local LLM providers (Ollama and GPT4All).

These helpers are intentionally provider-agnostic: they implement the raw
networking / model-inference plumbing (health checks, timeouts, retries,
streaming, thread-safe inference, model caching and cleanup) so the
``OllamaProvider`` and ``GPT4AllProvider`` classes in the AI engines can stay
thin and consistent across the duplicate engine modules.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import httpx

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"
OLLAMA_DEFAULT_TIMEOUT_SECONDS = 120
OLLAMA_DEFAULT_MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0


class OllamaClient:
    """Async client for the Ollama HTTP API.

    Supports:
    - Health check against ``/api/tags`` before generating.
    - Timeout on every request (defaults from settings).
    - Automatic retry with backoff on 5xx / transient transport errors.
    - Streaming-ready (``stream=True`` returns the aggregated response).
    - Structured logging of provider calls and failures.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        stream: bool | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL or OLLAMA_DEFAULT_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL or OLLAMA_DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS or OLLAMA_DEFAULT_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.OLLAMA_MAX_RETRIES or OLLAMA_DEFAULT_MAX_RETRIES
        self.stream = settings.OLLAMA_STREAM if stream is None else stream
        self._client: httpx.AsyncClient | None = None
        self._health_checked = False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client

    async def health_check(self) -> bool:
        """Return True when the Ollama server responds to /api/tags."""
        try:
            response = await self._get_client().get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as exc:
            logger.warning(
                "Ollama health check failed",
                base_url=self.base_url,
                error=str(exc),
            )
            return False

    async def generate(self, prompt: str, max_tokens: int | None = None, temperature: float = 0.2) -> str:
        """Generate a completion for ``prompt`` with retries and backoff."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": self.stream,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if self.stream:
            payload["stream"] = True

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                content = await self._request_generate(payload)
                if not content.strip():
                    raise RuntimeError("Ollama returned an empty completion")
                return content
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt >= self.max_retries:
                    logger.warning(
                        "Ollama generate failed (non-retryable)",
                        model=self.model,
                        status_code=exc.response.status_code,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    raise
                logger.warning(
                    "Ollama generate retryable failure",
                    model=self.model,
                    status_code=exc.response.status_code,
                    attempt=attempt + 1,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "Ollama generate transport error, retrying",
                    model=self.model,
                    attempt=attempt + 1,
                    error=str(exc),
                )
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

        raise RuntimeError(f"Ollama generate failed after {self.max_retries + 1} attempts: {last_error}")

    async def _request_generate(self, payload: dict[str, Any]) -> str:
        client = self._get_client()
        if not self._health_checked:
            if not await self.health_check():
                raise RuntimeError(
                    f"Ollama server unreachable at {self.base_url} "
                    "(is `ollama serve` running?)"
                )
            self._health_checked = True

        logger.info(
            "Ollama generate request",
            model=self.model,
            base_url=self.base_url,
            stream=payload.get("stream", False),
        )
        response = await client.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()

        if payload.get("stream"):
            content_parts: list[str] = []
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content_parts.append(chunk.get("response", ""))
                if chunk.get("done"):
                    break
            return "".join(content_parts)

        data = response.json()
        return str(data.get("response", ""))

    async def aclose(self) -> None:
        """Close the underlying HTTP client and reset health-check state."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._health_checked = False


class GPT4AllModel:
    """Thread-safe singleton wrapper around the gpt4all Python bindings.

    - Lazy loading: the (large) model is only downloaded/loaded on first use.
    - Singleton: one model instance is shared process-wide to avoid reloading.
    - Thread-safe inference: generation is serialized behind a lock.
    - Cleanup: ``close()`` releases the model reference.
    """

    _model_instance: Any | None = None
    _load_lock = threading.Lock()

    def __init__(
        self,
        model: str | None = None,
        model_path: str | None = None,
        threads: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model_name = model or settings.GPT4ALL_MODEL
        self.model_path = model_path if model_path is not None else settings.GPT4ALL_MODEL_PATH
        self.threads = threads if threads is not None else settings.GPT4ALL_THREADS
        self.max_tokens = max_tokens or settings.GPT4ALL_MAX_TOKENS or 1500
        self._local_lock = threading.Lock()

    def _load_model(self) -> Any:
        """Import and load the GPT4All model (module-level singleton)."""
        if type(self)._model_instance is not None:
            return type(self)._model_instance

        with type(self)._load_lock:
            if type(self)._model_instance is not None:
                return type(self)._model_instance
            try:
                from gpt4all import GPT4All as GPT4AllBinding
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "The 'gpt4all' package is not installed. "
                    "Install it with `pip install gpt4all` to use the GPT4All provider."
                ) from exc

            logger.info(
                "Loading GPT4All model",
                model=self.model_name,
                model_path=self.model_path,
                threads=self.threads,
            )
            model = GPT4AllBinding(
                self.model_name,
                model_path=self.model_path,
                n_threads=self.threads,
            )
            type(self)._model_instance = model
            return model

    def generate(self, prompt: str, max_tokens: int | None = None, temperature: float = 0.2) -> str:
        """Run thread-safe synchronous inference against the cached model."""
        model = self._load_model()
        with self._local_lock:
            return str(
                model.generate(
                    prompt,
                    max_tokens=max_tokens or self.max_tokens,
                    temp=temperature,
                )
            )

    async def agenerate(self, prompt: str, max_tokens: int | None = None, temperature: float = 0.2) -> str:
        """Async wrapper that offloads blocking inference to a worker thread."""
        return await asyncio.to_thread(self.generate, prompt, max_tokens, temperature)

    def close(self) -> None:
        """Release the cached model instance (no-op when never loaded)."""
        if type(self)._model_instance is not None:
            type(self)._model_instance = None
            logger.info("GPT4All model released from memory")
