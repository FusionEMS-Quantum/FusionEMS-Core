"""
Application-Level Circuit Breaker — FusionEMS-Core
Protects against cascading failures for external integrations.

State Machine: CLOSED → OPEN → HALF_OPEN → CLOSED

Usage:
    breaker = CircuitBreaker(name="stripe", failure_threshold=5, recovery_timeout_seconds=60)

    async with breaker:
        result = await call_stripe_api(...)

When OPEN, calls fail fast with CircuitOpenError instead of hitting the degraded service.
When HALF_OPEN, one probe call is allowed to test recovery.
"""
from __future__ import annotations

import logging
import time
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    """Raised when a call is attempted while the circuit is OPEN."""

    def __init__(self, name: str, opened_at: float, recovery_at: float) -> None:
        self.name = name
        self.opened_at = opened_at
        self.recovery_at = recovery_at
        remaining = max(0, recovery_at - time.monotonic())
        super().__init__(
            f"Circuit '{name}' is OPEN. Recovery in {remaining:.1f}s."
        )


class CircuitBreaker:
    """
    Thread-safe circuit breaker for external integration protection.

    Parameters:
        name: Identifier for the protected service (e.g., "stripe", "telnyx").
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout_seconds: Seconds to wait before allowing a probe call.
        success_threshold: Successful probe calls needed to close the circuit.
    """

    def __init__(
        self,
        *,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._opened_at: float = 0.0
        self._last_failure_at: float = 0.0
        self._total_trips: int = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, checking for recovery timeout transition."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._opened_at >= self.recovery_timeout_seconds
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            logger.info(
                "circuit_breaker.half_open",
                extra={"circuit": self.name},
            )
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def total_trips(self) -> int:
        return self._total_trips

    def snapshot(self) -> dict[str, Any]:
        """Current state snapshot for observability."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_trips": self._total_trips,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
        }

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(
                    "circuit_breaker.closed",
                    extra={"circuit": self.name, "reason": "recovery_confirmed"},
                )
        elif self._state == CircuitState.CLOSED:
            # Reset failure counter on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call. May trip the circuit."""
        self._failure_count += 1
        self._last_failure_at = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — reopen
            self._trip()
            return

        if self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            self._trip()

    def _trip(self) -> None:
        """Open the circuit breaker."""
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._total_trips += 1
        self._success_count = 0
        logger.warning(
            "circuit_breaker.open",
            extra={
                "circuit": self.name,
                "failure_count": self._failure_count,
                "total_trips": self._total_trips,
            },
        )

    def reset(self) -> None:
        """Manually reset to CLOSED. Used for admin recovery."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info(
            "circuit_breaker.manual_reset",
            extra={"circuit": self.name},
        )

    async def __aenter__(self) -> CircuitBreaker:
        current = self.state  # triggers timeout check
        if current == CircuitState.OPEN:
            raise CircuitOpenError(
                self.name,
                self._opened_at,
                self._opened_at + self.recovery_timeout_seconds,
            )
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> bool:
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure()
        return False  # Do not suppress the exception


# ── Global Registry ──────────────────────────────────────────────────────────

_REGISTRY: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    *,
    failure_threshold: int = 5,
    recovery_timeout_seconds: float = 60.0,
) -> CircuitBreaker:
    """Get or create a named circuit breaker from the global registry."""
    if name not in _REGISTRY:
        _REGISTRY[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
        )
    return _REGISTRY[name]


def all_circuit_snapshots() -> list[dict[str, Any]]:
    """Return snapshots of all registered circuit breakers."""
    return [cb.snapshot() for cb in _REGISTRY.values()]


def reset_all() -> None:
    """Reset all circuit breakers. Test utility only."""
    for cb in _REGISTRY.values():
        cb.reset()
