"""
Circuit Breaker — Unit Tests
Covers: state machine transitions, failure thresholds, recovery timeout,
half-open probing, manual reset, registry, observability snapshots.

DIRECTIVE REQUIREMENT: Application-level circuit breaking.
"""
from __future__ import annotations

import time

import pytest

from core_app.reliability.circuit_breaker import (
    _REGISTRY,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    all_circuit_snapshots,
    get_circuit_breaker,
    reset_all,
)

# ── State Machine Tests ──────────────────────────────────────────────────────

class TestCircuitBreakerStateMachine:
    """Verify CLOSED → OPEN → HALF_OPEN → CLOSED transitions."""

    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.total_trips == 0

    def test_failures_below_threshold_stay_closed(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 2

    def test_failures_at_threshold_trip_to_open(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.total_trips == 1

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_open_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.01)
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.01)
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.total_trips == 2

    def test_multiple_trips_counted(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.01)
        for _ in range(3):
            cb.record_failure()
            time.sleep(0.02)
            _ = cb.state  # trigger half-open check
            cb.record_failure()  # re-trip
        assert cb.total_trips == 4  # initial + 3 re-trips

    def test_manual_reset(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# ── Context Manager Tests ────────────────────────────────────────────────────

class TestCircuitBreakerContextManager:
    """Async context manager integration."""

    async def test_closed_circuit_allows_call(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        async with cb:
            pass  # call succeeds
        assert cb.state == CircuitState.CLOSED

    async def test_open_circuit_raises_error(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError) as exc_info:
            async with cb:
                pass
        assert "OPEN" in str(exc_info.value)
        assert exc_info.value.name == "test"

    async def test_exception_in_context_records_failure(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=5)
        with pytest.raises(ValueError):
            async with cb:
                raise ValueError("simulated error")
        assert cb.failure_count == 1

    async def test_success_in_context_records_success(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        async with cb:
            pass
        assert cb.failure_count == 0  # reset on success


# ── Snapshot / Observability Tests ───────────────────────────────────────────

class TestCircuitBreakerObservability:
    """Snapshot output for founder tech command center."""

    def test_snapshot_has_required_fields(self) -> None:
        cb = CircuitBreaker(name="stripe", failure_threshold=5, recovery_timeout_seconds=30)
        snap = cb.snapshot()
        assert snap["name"] == "stripe"
        assert snap["state"] == "CLOSED"
        assert snap["failure_count"] == 0
        assert snap["failure_threshold"] == 5
        assert snap["recovery_timeout_seconds"] == 30

    def test_snapshot_reflects_open_state(self) -> None:
        cb = CircuitBreaker(name="telnyx", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        snap = cb.snapshot()
        assert snap["state"] == "OPEN"
        assert snap["failure_count"] == 2
        assert snap["total_trips"] == 1


# ── Registry Tests ───────────────────────────────────────────────────────────

class TestCircuitBreakerRegistry:
    """Global registry for named circuit breakers."""

    def setup_method(self) -> None:
        _REGISTRY.clear()

    def test_get_or_create(self) -> None:
        cb1 = get_circuit_breaker("stripe")
        cb2 = get_circuit_breaker("stripe")
        assert cb1 is cb2

    def test_different_names_different_breakers(self) -> None:
        cb1 = get_circuit_breaker("stripe")
        cb2 = get_circuit_breaker("telnyx")
        assert cb1 is not cb2

    def test_all_snapshots(self) -> None:
        get_circuit_breaker("stripe")
        get_circuit_breaker("telnyx")
        get_circuit_breaker("officeally")
        snaps = all_circuit_snapshots()
        assert len(snaps) == 3
        names = {s["name"] for s in snaps}
        assert names == {"stripe", "telnyx", "officeally"}

    def test_reset_all(self) -> None:
        cb = get_circuit_breaker("stripe", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        reset_all()
        assert cb.state == CircuitState.CLOSED


# ── CircuitOpenError Tests ───────────────────────────────────────────────────

class TestCircuitOpenError:
    """Error object carries diagnostic information."""

    def test_error_contains_circuit_name(self) -> None:
        err = CircuitOpenError("stripe", 100.0, 160.0)
        assert err.name == "stripe"
        assert "stripe" in str(err)

    def test_error_contains_timing_info(self) -> None:
        err = CircuitOpenError("telnyx", 100.0, 160.0)
        assert err.opened_at == 100.0
        assert err.recovery_at == 160.0


# ── EMS Integration Scenarios ────────────────────────────────────────────────

class TestEMSIntegrationCircuitBreakers:
    """Real-world patterns for FusionEMS external integrations."""

    async def test_stripe_circuit_breaker_flow(self) -> None:
        """Simulate Stripe API going down and recovering."""
        cb = CircuitBreaker(
            name="stripe",
            failure_threshold=3,
            recovery_timeout_seconds=0.01,
        )
        # 3 failures trip the breaker
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery window
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # Probe succeeds
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    async def test_telnyx_circuit_breaker_prevents_cascading(self) -> None:
        """Telnyx down should not cascade to billing or dispatch."""
        telnyx_cb = CircuitBreaker(name="telnyx", failure_threshold=2)
        billing_cb = CircuitBreaker(name="stripe", failure_threshold=5)

        # Telnyx trips
        telnyx_cb.record_failure()
        telnyx_cb.record_failure()
        assert telnyx_cb.state == CircuitState.OPEN

        # Billing should be unaffected
        assert billing_cb.state == CircuitState.CLOSED
        billing_cb.record_success()
        assert billing_cb.state == CircuitState.CLOSED

    def test_success_threshold_requires_multiple_probes(self) -> None:
        """For critical services, require 2 successes before closing."""
        cb = CircuitBreaker(
            name="officeally",
            failure_threshold=1,
            recovery_timeout_seconds=0.01,
            success_threshold=2,
        )
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # not yet closed

        cb.record_success()
        assert cb.state == CircuitState.CLOSED  # now closed
