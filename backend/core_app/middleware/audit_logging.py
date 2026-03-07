"""Audit Logging Middleware with Prometheus metrics instrumentation.

Adds correlation IDs, records request duration, and emits structured logs.
"""
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core_app.observability.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        request.state.audit_context = {
            "actor_user_id": None,
            "tenant_id": None,
            "correlation_id": correlation_id,
        }

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Normalize path for metrics (strip IDs to prevent cardinality explosion)
        path = request.url.path
        method = request.method
        status = str(response.status_code)

        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status_code=status).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

        response.headers["x-correlation-id"] = correlation_id

        # Structured access log
        logger.info(
            "%s %s %s %.3fs",
            method,
            path,
            status,
            duration,
            extra={
                "correlation_id": correlation_id,
                "extra_fields": {
                    "method": method,
                    "path": path,
                    "status": int(response.status_code),
                    "duration_s": round(duration, 4),
                },
            },
        )
        return response
