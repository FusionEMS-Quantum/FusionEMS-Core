#!/usr/bin/env python3
"""Validate authentication and access-control production readiness.

This gate enforces three non-negotiable conditions:
1) Core auth routes exist (login/refresh/logout/register/reset/invite).
2) Auth router is mounted under /api/v1 in the main app assembly.
3) Production config fails closed for insecure auth settings.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Ensure import-time DB engine initialization has a parseable URL.
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/fusionems")
if not os.environ.get("OSS_TTS_PIPER_SPEAKER_ID"):
    os.environ["OSS_TTS_PIPER_SPEAKER_ID"] = "0"

from core_app.api.auth_router import router as auth_router  # noqa: E402
from core_app.core.config import Settings  # noqa: E402


def _required_auth_routes() -> set[tuple[str, str]]:
    return {
        ("POST", "/auth/login"),
        ("POST", "/auth/register"),
        ("POST", "/auth/invite"),
        ("POST", "/auth/invite/accept"),
        ("POST", "/auth/password-reset"),
        ("POST", "/auth/password-reset/confirm"),
        ("POST", "/auth/refresh"),
        ("POST", "/auth/logout"),
    }


def _actual_auth_routes() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for route in auth_router.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        for method in methods:
            if method in {"POST", "GET", "PUT", "PATCH", "DELETE"}:
                pairs.add((method, path))
    return pairs


def _assert_router_mounts() -> None:
    main_py = (BACKEND / "core_app" / "main.py").read_text(encoding="utf-8")
    required_snippets = (
        'app.include_router(auth_router, prefix="/api/v1")',
        'app.include_router(microsoft_auth_router, prefix="/api/v1")',
    )
    missing = [snippet for snippet in required_snippets if snippet not in main_py]
    if missing:
        raise AssertionError(f"missing auth router mounts: {missing}")


@contextmanager
def _temporary_env(env: dict[str, str]):
    previous = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _prod_env_baseline() -> dict[str, str]:
    return {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://u:p@localhost:5432/fusionems",
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_SECRET_KEY": "prod-random-super-long-secret-key-000000000000000001",
        "STRIPE_SECRET_KEY": "sk_live_dummy",
        "STRIPE_WEBHOOK_SECRET": "whsec_dummy",
        "LOB_API_KEY": "lob_dummy",
        "LOB_WEBHOOK_SECRET": "lob_webhook_dummy",
        "TELNYX_API_KEY": "telnyx_dummy",
        "TELNYX_FROM_NUMBER": "+15555550123",
        "CENTRAL_BILLING_PHONE_E164": "+15555550124",
        "TELNYX_PUBLIC_KEY": "cHVibGljX2tleV9kdW1teQ==",
        "IVR_AUDIO_BASE_URL": "https://assets.example.com/audio",
        "FAX_CLASSIFY_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/fax",
        "AWS_REGION": "us-east-1",
        "SYSTEM_TENANT_ID": "00000000-0000-0000-0000-000000000001",
        "LOB_EVENTS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/lob",
        "STRIPE_EVENTS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/stripe",
        "NERIS_PACK_IMPORT_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/neris-import",
        "NERIS_PACK_COMPILE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/neris-compile",
        "NERIS_EXPORT_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/neris-export",
        "NEMSIS_EXPORT_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/nemsis-export",
        "STATEMENTS_TABLE": "fusionems_statements",
        "LOB_EVENTS_TABLE": "fusionems_lob_events",
        "STRIPE_EVENTS_TABLE": "fusionems_stripe_events",
        "TENANTS_TABLE": "fusionems_tenants",
        "GRAPH_TENANT_ID": "11111111-1111-1111-1111-111111111111",
        "GRAPH_CLIENT_ID": "22222222-2222-2222-2222-222222222222",
        "GRAPH_CLIENT_SECRET": "graph_client_secret_dummy",
        "GRAPH_FOUNDER_EMAIL": "founder@fusionemsquantum.com",
        "MICROSOFT_REDIRECT_URI": "https://api.fusionemsquantum.com/api/v1/auth/microsoft/callback",
        "MICROSOFT_POST_LOGIN_URL": "https://app.fusionemsquantum.com/dashboard",
        "MICROSOFT_FOUNDER_POST_LOGIN_URL": "https://app.fusionemsquantum.com/dashboard?next=%2Ffounder",
        "MICROSOFT_POST_LOGOUT_URL": "https://app.fusionemsquantum.com/login",
        "SESSION_COOKIE_SAMESITE": "lax",
    }


def _assert_fail_closed_prod_settings() -> None:
    baseline = _prod_env_baseline()

    with _temporary_env({**baseline, "AUTH_MODE": "local", "SESSION_COOKIE_SECURE": "true"}):
        try:
            Settings()
        except ValueError as exc:
            if "AUTH_MODE" not in str(exc):
                raise AssertionError(f"expected AUTH_MODE fail-close error, got: {exc}") from exc
        else:
            raise AssertionError("expected Settings() to fail when AUTH_MODE=local in production")

    with _temporary_env({**baseline, "AUTH_MODE": "cognito", "SESSION_COOKIE_SECURE": "false"}):
        try:
            Settings()
        except ValueError as exc:
            if "SESSION_COOKIE_SECURE" not in str(exc):
                raise AssertionError(
                    f"expected SESSION_COOKIE_SECURE fail-close error, got: {exc}"
                ) from exc
        else:
            raise AssertionError(
                "expected Settings() to fail when SESSION_COOKIE_SECURE=false in production"
            )

    with _temporary_env({**baseline, "AUTH_MODE": "cognito", "SESSION_COOKIE_SECURE": "true"}):
        settings = Settings()
        assert settings.auth_mode == "cognito"
        assert settings.session_cookie_secure is True


def main() -> int:
    required = _required_auth_routes()
    actual = _actual_auth_routes()
    missing_routes = sorted(required - actual)
    if missing_routes:
        print(f"FAIL missing auth routes: {missing_routes}")
        return 1

    try:
        _assert_router_mounts()
        _assert_fail_closed_prod_settings()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        return 1

    print("OK auth surface validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
