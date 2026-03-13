#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy import text

# Ensure app settings can initialize in local validation contexts
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("JWT_SECRET_KEY", "release_validation_jwt_secret_key_1234567890")

from core_app.main import app  # noqa: E402
from core_app.api.dependencies import db_session_dependency, get_current_user  # noqa: E402
from core_app.schemas.auth import CurrentUser  # noqa: E402


@dataclass
class _ScalarResult:
    value: int = 0

    def scalar(self) -> int:
        return self.value


class _FakeDB:
    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "count(*) FROM system_alerts" in sql:
            return _ScalarResult(0)
        if "SELECT 1" in sql:
            return _ScalarResult(1)
        # Return zero scalar for non-critical checks
        return _ScalarResult(0)


def _override_user() -> CurrentUser:
    return CurrentUser(
        user_id="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000002",
        role="founder",
    )


def _override_db():
    yield _FakeDB()


def _validate_telnyx_runtime() -> dict[str, object]:
    import requests

    target_number = "+1-888-365-0144"
    api_key = os.getenv("TELNYX_API_KEY", "")
    if not api_key:
        return {
            "checked": False,
            "healthy": False,
            "number": target_number,
            "reason": "TELNYX_API_KEY not configured in runtime",
        }

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(
            "https://api.telnyx.com/v2/phone_numbers",
            params={"filter[phone_number]": target_number.replace("-", "")},
            headers=headers,
            timeout=15,
        )
        ok = resp.status_code < 300 and isinstance(resp.json().get("data"), list) and len(resp.json().get("data")) > 0
        return {
            "checked": True,
            "healthy": bool(ok),
            "number": target_number,
            "http_status": resp.status_code,
            "match_count": len(resp.json().get("data", []) if resp.headers.get("content-type", "").startswith("application/json") else []),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "checked": True,
            "healthy": False,
            "number": target_number,
            "reason": str(exc),
        }


def main() -> int:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[db_session_dependency] = _override_db

    with TestClient(app) as client:
        live = client.get("/api/v1/platform/live-status", headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    telnyx_runtime = _validate_telnyx_runtime()

    result = {
        "live_status_http": live.status_code,
        "live_status": live.json() if live.status_code == 200 else {"error": live.text},
        "telnyx_runtime_validation": telnyx_runtime,
    }

    print(json.dumps(result, indent=2))

    live_ok = live.status_code == 200 and isinstance(result["live_status"], dict)
    telnyx_ok = bool(telnyx_runtime.get("healthy"))
    return 0 if (live_ok and telnyx_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
