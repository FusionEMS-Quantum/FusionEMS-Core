"""
Security headers middleware — adds Content Security Policy and other
defense-in-depth HTTP headers to all API responses.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

# Tightly scoped CSP: API-only backend, no HTML content served.
# Browsers should never render content from this origin directly.
_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'none';"
)

_SECURITY_HEADERS = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects security headers on every response.

    Note: HSTS (Strict-Transport-Security) is intentionally omitted here because
    it is set at the CDN/ALB layer in production (infra/terraform/modules/edge/)
    to avoid accidental HSTS pinning in non-HTTPS development environments.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
