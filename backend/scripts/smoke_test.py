from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    required: bool
    url: str
    method: str
    status_code: int | None
    duration_ms: int
    detail: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_base(url: str) -> str:
    return url.rstrip("/")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _check_http(
    *,
    session: requests.Session,
    name: str,
    method: str,
    url: str,
    expected_statuses: set[int],
    required: bool,
    json_payload: dict[str, Any] | None = None,
    timeout_seconds: int = 15,
) -> CheckResult:
    started = time.monotonic()
    status_code: int | None = None
    try:
        response = session.request(
            method=method,
            url=url,
            json=json_payload,
            timeout=timeout_seconds,
        )
        status_code = response.status_code
        ok = status_code in expected_statuses
        detail = f"expected={sorted(expected_statuses)} actual={status_code}"
        if not ok:
            body_preview = response.text[:280].replace("\n", " ")
            detail = f"{detail} body={body_preview}"
    except requests.RequestException as exc:
        ok = False
        detail = f"request_error={exc!s}"

    duration_ms = int((time.monotonic() - started) * 1000)
    return CheckResult(
        name=name,
        ok=ok,
        required=required,
        url=url,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        detail=detail,
    )


def _auth_token(
    *,
    session: requests.Session,
    api_base: str,
    email: str,
    password: str,
) -> tuple[str | None, CheckResult]:
    login_url = f"{api_base}/api/v1/auth/login"
    started = time.monotonic()
    try:
        login_resp = session.post(
            login_url,
            json={"email": email, "password": password},
            timeout=15,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        result = CheckResult(
            name="auth.login",
            ok=login_resp.status_code == 200,
            required=True,
            url=login_url,
            method="POST",
            status_code=login_resp.status_code,
            duration_ms=duration_ms,
            detail=f"expected=[200] actual={login_resp.status_code}",
        )
        if not result.ok:
            body_preview = login_resp.text[:280].replace("\n", " ")
            result.detail = f"{result.detail} body={body_preview}"
            return None, result

        token = login_resp.json().get("access_token")
        if not token:
            result.ok = False
            result.detail = "missing access_token in login response"
            return None, result
        return token, result
    except (requests.RequestException, ValueError, TypeError) as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        result = CheckResult(
            name="auth.login",
            ok=False,
            required=True,
            url=login_url,
            method="POST",
            status_code=None,
            duration_ms=duration_ms,
            detail=f"failed to execute login: {exc!s}",
        )
        return None, result


def main() -> int:
    api_base = os.getenv("SMOKE_API_BASE_URL") or os.getenv("BASE_URL")
    frontend_base = os.getenv("SMOKE_FRONTEND_URL") or api_base
    require_auth = _bool_env("SMOKE_REQUIRE_AUTH", default=False)
    report_path = Path(
        os.getenv(
            "SMOKE_REPORT_PATH",
            "/workspaces/FusionEMS-Core/artifacts/post_deploy_smoke_report.json",
        )
    )

    if not api_base:
        print("SMOKE_API_BASE_URL (or BASE_URL) is required")
        return 2

    api_base = _normalize_base(api_base)
    frontend_base = _normalize_base(frontend_base) if frontend_base else ""

    correlation_id = str(uuid.uuid4())
    session = requests.Session()
    session.headers.update({"X-Correlation-ID": correlation_id})

    checks: list[CheckResult] = []

    # Core reachability
    checks.append(
        _check_http(
            session=session,
            name="api.health",
            method="GET",
            url=f"{api_base}/health",
            expected_statuses={200},
            required=True,
        )
    )
    checks.append(
        _check_http(
            session=session,
            name="api.healthz",
            method="GET",
            url=f"{api_base}/healthz",
            expected_statuses={200},
            required=True,
        )
    )
    checks.append(
        _check_http(
            session=session,
            name="api.v1.health",
            method="GET",
            url=f"{api_base}/api/v1/health",
            expected_statuses={200},
            required=True,
        )
    )

    if frontend_base:
        checks.append(
            _check_http(
                session=session,
                name="frontend.login.page",
                method="GET",
                url=f"{frontend_base}/login",
                expected_statuses={200},
                required=True,
            )
        )

    # Auth + protected runtime checks
    auth_email = os.getenv("SMOKE_AUTH_EMAIL", "").strip()
    auth_password = os.getenv("SMOKE_AUTH_PASSWORD", "").strip()
    token: str | None = None

    if auth_email and auth_password:
        token, auth_check = _auth_token(
            session=session,
            api_base=api_base,
            email=auth_email,
            password=auth_password,
        )
        checks.append(auth_check)
    else:
        checks.append(
            CheckResult(
                name="auth.login",
                ok=not require_auth,
                required=require_auth,
                url=f"{api_base}/api/v1/auth/login",
                method="POST",
                status_code=None,
                duration_ms=0,
                detail="skipped (set SMOKE_AUTH_EMAIL and SMOKE_AUTH_PASSWORD)",
            )
        )

    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})

        checks.append(
            _check_http(
                session=session,
                name="platform.health.authenticated",
                method="GET",
                url=f"{api_base}/api/v1/platform/health",
                expected_statuses={200},
                required=True,
            )
        )
        checks.append(
            _check_http(
                session=session,
                name="nemsis.schema.cache-status",
                method="GET",
                url=f"{api_base}/api/v1/nemsis-manager/schema/cache-status",
                expected_statuses={200},
                required=True,
            )
        )
        checks.append(
            _check_http(
                session=session,
                name="nemsis.validate.endpoint",
                method="POST",
                url=f"{api_base}/api/v1/nemsis/validate",
                expected_statuses={200},
                required=True,
                json_payload={"incident": {}, "patient": {}},
            )
        )
        checks.append(
            _check_http(
                session=session,
                name="neris.onboarding.status",
                method="GET",
                url=f"{api_base}/api/v1/tenant/neris/onboarding/status",
                expected_statuses={200},
                required=True,
            )
        )
        checks.append(
            _check_http(
                session=session,
                name="neris.validate.endpoint",
                method="POST",
                url=f"{api_base}/api/v1/neris/validate",
                expected_statuses={200, 422},
                required=True,
                json_payload={"entity_type": "INCIDENT", "payload": {}},
            )
        )

    required_failed = [c for c in checks if c.required and not c.ok]
    optional_failed = [c for c in checks if (not c.required) and (not c.ok)]

    report = {
        "generated_at": _now_iso(),
        "api_base": api_base,
        "frontend_base": frontend_base,
        "correlation_id": correlation_id,
        "status": "failed" if required_failed else "passed",
        "required_failures": len(required_failed),
        "optional_failures": len(optional_failed),
        "checks": [asdict(c) for c in checks],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"status": report["status"], "report": str(report_path)}))
    return 1 if required_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
