"""HTTP client for the DevArchAI backend API.

Hardened around the constraints in the project spec:

- The resolved token is sent as ``Authorization: Bearer <token>`` for JWTs or
  ``X-API-Key: <token>`` for DevArchAI API keys (``sk-`` or legacy ``dk_``),
  and is never logged.
- Requests time out; idempotent requests (GET/DELETE/HEAD/OPTIONS) are retried
  on ``429``/``5xx`` with exponential backoff.
- Failures map to typed errors with a stable exit code, and the backend's
  request ID (``X-Request-ID``) is captured for support.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from devsec._version import __version__
from devsec.config import Config
from devsec.utils.errors import ApiError, AuthError, ConfigError

# All CLI calls go through the versioned API root.
_API_PREFIX = "/api/v1"

_RETRYABLE_METHODS = {"GET", "HEAD", "OPTIONS", "DELETE"}
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5

# Status codes that map to authentication problems.
_AUTH_STATUS = {401, 403}

_USER_AGENT = f"devsec-cli/{__version__}"


def _extract_detail(payload: dict[str, Any], status_code: int) -> str:
    """Pull a human-readable message out of a backend error body.

    Handles FastAPI's ``{"detail": ...}`` and the backend's legacy
    ``{"error": {"code": ..., "message": ...}}`` shapes.
    """
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = ".".join(str(p) for p in item.get("loc", []) if p != "body")
                msg = str(item.get("msg", "")).strip()
                parts.append(f"{loc}: {msg}" if loc else msg)
        if parts:
            return "; ".join(parts)
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail")
        if message:
            return str(message)
    error = payload.get("error")
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        message = error.get("message") or error.get("detail")
        if message:
            return str(message)
    return f"HTTP {status_code}"


def _hint_for_status(status_code: int, request_id: str | None = None) -> str | None:
    if status_code in _AUTH_STATUS:
        return "Run 'devsec auth login' to authenticate."
    if status_code == 404:
        return "The resource may have been deleted or the ID is wrong."
    if status_code == 409:
        return "The resource conflicts with the current state on the server."
    if status_code == 422:
        return "Check the request values and try again."
    if status_code == 429:
        return "Rate limit exceeded. Wait a moment and try again."
    if status_code >= 500:
        suffix = f" (request ID {request_id})" if request_id else ""
        return f"The DevArchAI service had a problem.{suffix} Try again later."
    return None


class ApiClient:
    """Thin, hardened client over the backend REST API."""

    def __init__(
        self,
        config: Config,
        *,
        token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = _MAX_RETRIES,
        transport: Any = None,
    ) -> None:
        self._config = config
        self._token_override = token
        self._max_retries = max_retries
        api_url = config.api_url.rstrip("/")
        if not api_url.startswith(("http://", "https://")):
            raise ConfigError(
                f"Invalid API URL: {api_url}",
                hint="Set DEVSEC_API_URL or run 'devsec config set api-url <url>'.",
            )
        self.api_url = api_url
        self._client = httpx.Client(
            base_url=api_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"User-Agent": _USER_AGENT},
            transport=transport,
        )

    # ------------------------------------------------------------------
    # Auth header
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        token = self._token_override
        if token is None:
            token = self._config.token
        if not token:
            return {}
        if token.startswith(("sk-", "dk_")):
            return {"X-API-Key": token}
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Request plumbing
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        retry: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        url = f"{_API_PREFIX}{path}"
        merged_headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        attempts = 0
        while True:
            try:
                response = self._client.request(method, url, headers=merged_headers, **kwargs)
            except httpx.TimeoutException as exc:
                if self._should_retry(method, attempts) and retry:
                    attempts += 1
                    self._backoff(attempts)
                    continue
                raise ApiError(
                    f"Request to {self.api_url} timed out.",
                    hint="Check your connection and that the API is reachable.",
                    method=method,
                    url=url,
                ) from exc
            except httpx.RequestError as exc:
                raise ApiError(
                    f"Unable to reach the API at {self.api_url}.",
                    hint="Check DEVSEC_API_URL and that the service is running.",
                    method=method,
                    url=url,
                ) from exc

            if response.status_code < 400:
                return response
            if (
                self._should_retry(method, attempts)
                and retry
                and response.status_code in _RETRY_STATUS
            ):
                attempts += 1
                self._backoff(attempts)
                continue
            self._raise_for_status(response, method, url)

    def _should_retry(self, method: str, attempts: int) -> bool:
        return method in _RETRYABLE_METHODS and attempts < self._max_retries

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))

    def _raise_for_status(self, response: httpx.Response, method: str, url: str) -> None:
        status = response.status_code
        request_id = response.headers.get("x-request-id")
        try:
            payload = response.json() if response.content else {}
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        message = _extract_detail(payload, status)
        hint = _hint_for_status(status, request_id)

        if status in _AUTH_STATUS:
            message = message or "Authentication failed."
            raise AuthError(
                message,
                hint=hint,
                status_code=status,
                request_id=request_id,
                method=method,
                url=url,
            )
        if status == 404:
            raise ApiError(
                message
                if message and message != f"HTTP {status}"
                else f"Resource not found: {url}",
                hint=hint,
                status_code=status,
                request_id=request_id,
                method=method,
                url=url,
            )
        raise ApiError(
            message,
            hint=hint,
            status_code=status,
            request_id=request_id,
            method=method,
            url=url,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("POST", path, retry=False, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("DELETE", path, **kwargs)

    def get_json(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs).json()

    def post_json(self, path: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return self._request("POST", path, retry=False, json=payload, **kwargs).json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
