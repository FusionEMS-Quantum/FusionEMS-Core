from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api.dependencies import get_current_user
from core_app.api.founder_router import router
from core_app.schemas.auth import CurrentUser


def _build_client(*, role: str) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=role,
    )
    return TestClient(app)


def test_multi_agent_status_requires_founder_or_admin() -> None:
    client = _build_client(role="viewer")

    response = client.get("/api/v1/founder/operations/multi-agent/status")

    assert response.status_code == 403


def test_multi_agent_status_handles_missing_artifacts(monkeypatch, tmp_path) -> None:
    from core_app.api import founder_router

    monkeypatch.setattr(founder_router, "_repo_root", lambda: tmp_path)
    client = _build_client(role="founder")

    response = client.get("/api/v1/founder/operations/multi-agent/status")

    assert response.status_code == 200
    body = response.json()
    assert body["orchestration"]["status"] == "not_available"
    assert body["compliance_program"]["status"] == "not_available"
    assert body["nemsis"]["status"] == "not_available"
    assert body["neris"]["status"] == "not_available"


def test_multi_agent_status_returns_artifact_summary(monkeypatch, tmp_path) -> None:
    from core_app.api import founder_router

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "multi_agent_execution_report.json").write_text(
        """
        {
          "meta": {
            "mode": "validate",
            "generated_at_utc": "2026-03-09T23:37:49.607870+00:00"
          },
          "status": "warning",
          "lanes": [
            {"lane_id": "agent-2", "agent_label": "Backend", "status": "passed", "log_file": "artifacts/multi-agent-logs/agent-2.log"},
            {"lane_id": "agent-3", "agent_label": "AWS", "status": "failed", "log_file": "artifacts/multi-agent-logs/agent-3.log"},
            {"lane_id": "agent-7", "agent_label": "Audit", "status": "warning", "log_file": "artifacts/multi-agent-logs/agent-7.log"}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )
    (artifacts_dir / "compliance-evidence-manifest.json").write_text(
        """
        {
          "status": "pass",
          "generated_at_utc": "2026-03-09T23:37:49.672111+00:00",
          "missing_count": 0
        }
        """.strip(),
        encoding="utf-8",
    )
    (artifacts_dir / "nemsis-ci-report.json").write_text(
        """
        {
          "status": "NEMSIS-ready / validation-passing",
          "certification_status": "pending",
          "evidence": {"all_passed": true}
        }
        """.strip(),
        encoding="utf-8",
    )
    (artifacts_dir / "neris-ci-report.json").write_text(
        """
        {
          "status": "NERIS integration-ready / validation-passing",
          "certification_status": "pending",
          "evidence": {"all_passed": true}
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(founder_router, "_repo_root", lambda: tmp_path)
    client = _build_client(role="founder")

    response = client.get("/api/v1/founder/operations/multi-agent/status")

    assert response.status_code == 200
    body = response.json()
    assert body["orchestration"]["status"] == "warning"
    assert body["orchestration"]["failed_lane_count"] == 1
    assert body["orchestration"]["warning_lane_count"] == 1
    assert body["compliance_program"]["status"] == "pass"
    assert body["nemsis"]["status"] == "NEMSIS-ready / validation-passing"
    assert body["neris"]["status"] == "NERIS integration-ready / validation-passing"
    assert datetime.fromisoformat(body["as_of"]).tzinfo == UTC
