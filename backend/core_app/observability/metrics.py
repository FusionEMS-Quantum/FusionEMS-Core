"""Application-level Prometheus metrics.

Registers counters, histograms, and gauges for request tracking,
error classification, and infrastructure health.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# --- HTTP Request Metrics ---
HTTP_REQUESTS_TOTAL = Counter(
    "fusionems_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "fusionems_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# --- Error Classification ---
APP_ERRORS_TOTAL = Counter(
    "fusionems_app_errors_total",
    "Application errors by code",
    ["error_code", "status_code"],
)

# --- Infrastructure Gauges ---
DB_PROBE_LATENCY = Gauge(
    "fusionems_db_probe_latency_ms",
    "Last database probe latency in milliseconds",
)

REDIS_PROBE_LATENCY = Gauge(
    "fusionems_redis_probe_latency_ms",
    "Last Redis probe latency in milliseconds",
)

PLATFORM_HEALTH_SCORE = Gauge(
    "fusionems_platform_health_score",
    "Platform health score (0-100)",
)

# --- Incident Tracking ---
ACTIVE_INCIDENTS = Gauge(
    "fusionems_active_incidents",
    "Currently active platform incidents",
    ["severity"],
)

# --- Rate Limiting ---
RATE_LIMIT_REJECTIONS = Counter(
    "fusionems_rate_limit_rejections_total",
    "Rate limit rejections by tenant tier",
    ["tenant_tier"],
)

# --- AI Operations ---
AI_REQUESTS_TOTAL = Counter(
    "fusionems_ai_requests_total",
    "Total AI API calls",
    ["model", "status"],
)

AI_REQUEST_DURATION = Histogram(
    "fusionems_ai_request_duration_seconds",
    "AI API call duration",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)
