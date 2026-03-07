"""Tests for Prometheus metrics instruments."""
from core_app.observability.metrics import (
    ACTIVE_INCIDENTS,
    APP_ERRORS_TOTAL,
    DB_PROBE_LATENCY,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    PLATFORM_HEALTH_SCORE,
)


def test_http_counter_increments() -> None:
    before = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status_code="200")._value.get()
    HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status_code="200").inc()
    after = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status_code="200")._value.get()
    assert after == before + 1


def test_histogram_observes() -> None:
    HTTP_REQUEST_DURATION.labels(method="GET", endpoint="/test").observe(0.123)


def test_gauge_sets() -> None:
    DB_PROBE_LATENCY.set(15)
    assert DB_PROBE_LATENCY._value.get() == 15


def test_platform_health_score_gauge() -> None:
    PLATFORM_HEALTH_SCORE.set(95)
    assert PLATFORM_HEALTH_SCORE._value.get() == 95


def test_active_incidents_gauge() -> None:
    ACTIVE_INCIDENTS.labels(severity="CRITICAL").set(2)
    assert ACTIVE_INCIDENTS.labels(severity="CRITICAL")._value.get() == 2


def test_error_counter() -> None:
    APP_ERRORS_TOTAL.labels(error_code="TEST_ERROR", status_code="500").inc()
