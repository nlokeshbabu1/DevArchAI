"""Circuit breaker for the MCP live-context gateway.

Per-technology breaker so a failing provider for one technology never
degrades other technologies. States:

- ``closed``: requests allowed; failures counted.
- ``open``: requests short-circuited to ``skipped`` for the cooldown window.
- ``half_open``: a single probe request is allowed to test recovery.

The breaker never raises — an open breaker causes callers to return a
``skipped`` context so the scan pipeline is never affected.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

import structlog

from app.config import settings
from app.services.metrics import set_mcp_circuit_breaker

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Sliding failure-count circuit breaker."""

    def __init__(
        self,
        technology: str,
        failure_threshold: int | None = None,
        cooldown_seconds: float | None = None,
        half_open_success_threshold: int = 1,
    ) -> None:
        self.technology = technology
        self.failure_threshold = failure_threshold or settings.MCP_CIRCUIT_BREAKER_THRESHOLD
        self.cooldown_seconds = cooldown_seconds or settings.MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._opened_at: float | None = None

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def allow_request(self) -> bool:
        """Whether a request may be attempted for this technology."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self._opened_at and (time.monotonic() - self._opened_at) >= self.cooldown_seconds:
                self._transition(CircuitState.HALF_OPEN)
                return True
            return False
        # HALF_OPEN: allow a single probe request.
        return self._consecutive_successes == 0

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        self._consecutive_failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.half_open_success_threshold:
                self._transition(CircuitState.CLOSED)

    def record_failure(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._transition(CircuitState.OPEN)

    def _transition(self, new_state: CircuitState) -> None:
        logger.warning(
            "MCP_CIRCUIT_TRANSITION",
            technology=self.technology,
            from_state=self.state.value,
            to_state=new_state.value,
        )
        self.state = new_state
        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._consecutive_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._opened_at = None
        set_mcp_circuit_breaker(self.technology, new_state == CircuitState.OPEN)

    def reset(self) -> None:
        """Manually reset the breaker (e.g. after config/credential change)."""
        self._transition(CircuitState.CLOSED)

    def stats(self) -> dict[str, Any]:
        return {
            "technology": self.technology,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "cooldown_seconds": self.cooldown_seconds,
        }


class CircuitBreakerRegistry:
    """Registry of per-technology circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, technology: str) -> CircuitBreaker:
        if technology not in self._breakers:
            self._breakers[technology] = CircuitBreaker(technology)
        return self._breakers[technology]

    def reset_all(self) -> None:
        for breaker in self._breakers.values():
            breaker.reset()

    def stats(self) -> dict[str, Any]:
        return {name: b.stats() for name, b in self._breakers.items()}


# Singleton
_registry: CircuitBreakerRegistry | None = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit-breaker registry singleton."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(technology: str) -> CircuitBreaker:
    return get_circuit_breaker_registry().get(technology)
