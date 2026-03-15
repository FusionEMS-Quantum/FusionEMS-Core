from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api import platform_core_router
from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import Settings
from core_app.schemas.auth import CurrentUser


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar(self) -> object:
        return self._value

    def fetchone(self) -> tuple[object]:
        return (self._value,)


class _DBStub:
    def execute(self, statement, params: dict[str, object] | None = None) -> _ScalarResult:  # noqa: ANN001
        sql = str(statement)
        if "count(*) FROM system_alerts" in sql:
            return _ScalarResult(0)
        if "SELECT version_num FROM alembic_version" in sql:
            return _ScalarResult("rev_test")
        if "SELECT EXISTS(SELECT 1 FROM information_schema.tables" in sql:
            return _ScalarResult(True)
        if "count(*) FROM tenants" in sql:
            return _ScalarResult(0)
        return _ScalarResult(1)


def _build_client(db_stub: _DBStub) -> TestClient:
    app = FastAPI()
    app.include_router(platform_core_router.router)

    def _override_db():
        yield db_stub

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role="founder",
    )
    return TestClient(app)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "environment": "staging",
        "auth_mode": "fusion_jwt",
        "database_url": "postgresql://user:pass@localhost:5432/fusionems",
        "redis_url": "redis://unit-test:6379/0",
        "graph_tenant_id": "00000000-0000-0000-0000-000000000010",
        "graph_client_id": "00000000-0000-0000-0000-000000000020",
        "graph_client_secret": "graph_live_secret_value",
        "graph_founder_email": "founder@example.com",
        "microsoft_redirect_uri": "https://api.example.com/api/v1/auth/microsoft/callback",
        "stripe_secret_key": "stripe_ci_test_key_not_real",
        "stripe_webhook_secret": "whsec_live_secret_value",
        "telnyx_api_key": "telnyx_live_secret_value",
        "telnyx_from_number": "+18883650144",
        "central_billing_phone_e164": "+1-888-365-0144",
        "telnyx_public_key": "telnyx_public_key_material",
        "telnyx_messaging_profile_id": "profile_123",
        "officeally_sftp_host": "sftp.officeally.example",
        "officeally_sftp_username": "officeally-user",
        "officeally_sftp_password": "officeally-secret",
        "lob_api_key": "lob_live_secret_value",
        "lob_webhook_secret": "lob_webhook_secret_value",
        "nemsis_cta_endpoint": "https://cta.example.test/ws",
        "nemsis_cta_username": "cta-user",
        "nemsis_cta_password": "cta-password",
        "nemsis_cta_organization": "Wisconsin Demo Org",
        "nemsis_national_endpoint": "https://national.example.test/ws",
        "nemsis_local_schematron_dir": "/tmp/nemsis/schematron",
        "nemsis_api_key": "nemsis_state_api_key",
        "nemsis_org_id": "WI-12345",
        "nemsis_export_queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/nemsis-export",
        "neris_api_key": "neris_api_key_value",
        "neris_export_queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/neris-export",
    }
    base.update(overrides)
    return Settings(**base)


def test_integration_state_table_marks_placeholder_values_not_ready() -> None:
    settings = _settings()

    state = settings.integration_state_table()

    assert state["stripe"]["configured"] is False
    assert state["stripe"]["status"] == "placeholder_configured"
    assert state["stripe"]["placeholder_fields"] == ["STRIPE_SECRET_KEY"]
    assert state["stripe"]["missing"] == []


def test_live_status_reports_artifact_backed_compliance_and_placeholder_blockers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "nemsis-ci-report.json").write_text(
        """
        {
          "status": "NEMSIS-ready / validation-passing",
          "certification_status": "Not certified - pending formal NEMSIS compliance process",
          "evidence": {"all_passed": true}
        }
        """.strip(),
        encoding="utf-8",
    )
    (artifacts_dir / "neris-ci-report.json").write_text(
        """
        {
          "status": "NERIS integration-ready / validation-passing",
          "certification_status": "Not certified - pending formal NERIS acceptance process",
          "evidence": {"all_passed": true}
        }
        """.strip(),
        encoding="utf-8",
    )

    class _RedisConnection:
        def ping(self) -> bool:
            return True

    class _RedisModule:
        @staticmethod
        def from_url(*args, **kwargs) -> _RedisConnection:  # noqa: ANN002, ANN003
            return _RedisConnection()

    monkeypatch.setattr(platform_core_router, "get_settings", lambda: _settings())
    monkeypatch.setattr(platform_core_router, "_repo_root", lambda: tmp_path)
    monkeypatch.setitem(sys.modules, "redis", _RedisModule)

    client = _build_client(_DBStub())

    response = client.get("/api/v1/platform/live-status")

    assert response.status_code == 200
    body = response.json()
    assert body["integration_state"]["stripe"]["configured"] is False
    assert body["integration_state"]["stripe"]["placeholder_fields"] == ["STRIPE_SECRET_KEY"]
    assert any("stripe:STRIPE_SECRET_KEY" in blocker for blocker in body["release_blockers"])
    assert body["nemsis"]["local_schematron_configured"] is True
    assert body["nemsis"]["cta_endpoint_ready"] is True
    assert body["nemsis"]["national_endpoint_ready"] is True
    assert body["nemsis"]["validation_status"] == "NEMSIS-ready / validation-passing"
    assert (
        body["nemsis"]["certification_status"]
        == "Not certified - pending formal NEMSIS compliance process"
    )
    assert body["neris"]["validation_status"] == "NERIS integration-ready / validation-passing"
    assert (
        body["neris"]["certification_status"]
        == "Not certified - pending formal NERIS acceptance process"
    )


def test_release_readiness_rejects_placeholder_stripe_secret(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform_core_router, "get_settings", lambda: _settings())

    client = _build_client(_DBStub())

    response = client.get("/api/v1/platform/release-readiness")

    assert response.status_code == 200
    body = response.json()
    stripe_gate = next(gate for gate in body["gates"] if gate["name"] == "stripe_configured")
    assert stripe_gate["passed"] is False
    assert "placeholder_fields=STRIPE_SECRET_KEY" in stripe_gate["detail"]
