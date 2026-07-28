"""Search client for live AWS documentation retrieval.

Provides a pluggable search interface for fetching live AWS documentation
using web search APIs. Supports multiple search backends (SerpAPI, Bing, etc.)
with automatic fallback to curated content when search is unavailable.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SearchClient(ABC):
    """Abstract base class for search clients."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        """Search for documents matching the query.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: title, snippet, url
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the search client is available and configured."""
        ...


class SerpAPIClient(SearchClient):
    """Search client using SerpAPI (Google Search API).

    Requires SERPAPI_KEY environment variable.
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._available = False

    def _ensure_configured(self) -> None:
        if self._available:
            return

        if not self._api_key:
            import os
            self._api_key = os.environ.get("SERPAPI_KEY")

        if self._api_key:
            self._available = True

    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        self._ensure_configured()
        if not self._available:
            return []

        try:
            import requests
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self._api_key,
                    "num": max_results,
                    "engine": "google",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                })

            return results

        except Exception as exc:
            logger.warning(f"SERPAPI_SEARCH_FAILED: {exc}")
            return []

    def health_check(self) -> bool:
        self._ensure_configured()
        return self._available


class BingSearchClient(SearchClient):
    """Search client using Bing Search API.

    Requires BING_SEARCH_KEY environment variable.
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._available = False

    def _ensure_configured(self) -> None:
        if self._available:
            return

        if not self._api_key:
            import os
            self._api_key = os.environ.get("BING_SEARCH_KEY")

        if self._api_key:
            self._available = True

    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        self._ensure_configured()
        if not self._available:
            return []

        try:
            import requests
            headers = {"Ocp-Apim-Subscription-Key": self._api_key}
            response = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers=headers,
                params={
                    "q": query,
                    "count": max_results,
                    "mkt": "en-US",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("webPages", {}).get("value", [])[:max_results]:
                results.append({
                    "title": item.get("name", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("url", ""),
                })

            return results

        except Exception as exc:
            logger.warning(f"BING_SEARCH_FAILED: {exc}")
            return []

    def health_check(self) -> bool:
        self._ensure_configured()
        return self._available


class FallbackSearchClient(SearchClient):
    """Fallback search client that returns empty results.

    Used when no search API is configured.
    """

    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        logger.debug(f"FALLBACK_SEARCH_NO_OP query={query[:80]}")
        return []

    def health_check(self) -> bool:
        return True


def get_search_client() -> SearchClient:
    """Get the appropriate search client based on configuration.

    Tries SerpAPI first, then Bing, then falls back to no-op.
    """
    # Try SerpAPI
    serpapi_client = SerpAPIClient()
    if serpapi_client.health_check():
        logger.info("SEARCH_CLIENT_INITIALIZED client=serpapi")
        return serpapi_client

    # Try Bing
    bing_client = BingSearchClient()
    if bing_client.health_check():
        logger.info("SEARCH_CLIENT_INITIALIZED client=bing")
        return bing_client

    # Fallback
    logger.info("SEARCH_CLIENT_INITIALIZED client=fallback (no search API configured)")
    return FallbackSearchClient()
