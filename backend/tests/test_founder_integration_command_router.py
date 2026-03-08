"""API tests for founder integration command router write endpoints."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.api.founder_integration_command_router import router
from core_app.core.errors import AppError
from core_app.schemas.auth import CurrentUser


@dataclass
class _DBStub:
    commit_calls: int = 0
    refreshed: list[object] = field(default_factory=list)

    def commit(self) -> None:
        self.commit_calls += 1

    def refresh(self, obj: object) -> None:
        self.refreshed.append(obj)


@dataclass
class _SyncJobModel:
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_connector_install_id: uuid.UUID
    direction: str
    state: str
    started_at: datetime | None
    completed_at: datetime | None
    records_attempted: int
    records_succeeded: int
    records_failed: int
    error_summary: dict[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass
class _DeadLetterModel:
    id: uuid.UUID
    tenant_id: uuid.UUID
    connector_sync_job_id: uuid.UUID
    external_record_ref: str
    reason: str
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime


def _build_client(db_stub: _DBStub, current_user: CurrentUser) -> TestClient:
    app = FastAPI()

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response(trace_id=None))

    app.include_router(router)

    def _override_db():
        yield db_stub

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def test_create_sync_job_success_commits_and_scopes_tenant() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    install_id = uuid.uuid4()
    db_stub = _DBStub()
    client = _build_client(
        db_stub,
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="founder"),
    )

    created = datetime.now(UTC)
    sync_job = _SyncJobModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        tenant_connector_install_id=install_id,
        direction="OUTBOUND",
        state="QUEUED",
        started_at=None,
        completed_at=None,
        records_attempted=0,
        records_succeeded=0,
        records_failed=0,
        error_summary={"x12_payload_base64": "dGVzdA=="},
        created_at=created,
        updated_at=created,
    )

    with patch("core_app.api.founder_integration_command_router.FounderCommandDomainService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_connector_sync_job.return_value = sync_job

        response = client.post(
            "/api/v1/founder/integration-command/sync-jobs",
            json={
                "tenant_connector_install_id": str(install_id),
                "direction": "OUTBOUND",
                "state": "QUEUED",
                "records_attempted": 0,
                "records_succeeded": 0,
                "records_failed": 0,
                "error_summary": {"x12_payload_base64": "dGVzdA=="},
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["records_failed"] == 0

    svc.create_connector_sync_job.assert_called_once_with(
        tenant_id=tenant_id,
        actor_user_id=user_id,
        tenant_connector_install_id=install_id,
        direction="OUTBOUND",
        state="QUEUED",
        records_attempted=0,
        records_succeeded=0,
        records_failed=0,
        error_summary={"x12_payload_base64": "dGVzdA=="},
    )
    assert db_stub.commit_calls == 1
    assert db_stub.refreshed == [sync_job]


def test_create_sync_job_app_error_propagates() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    install_id = uuid.uuid4()
    db_stub = _DBStub()
    client = _build_client(
        db_stub,
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="founder"),
    )

    with patch("core_app.api.founder_integration_command_router.FounderCommandDomainService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_connector_sync_job.side_effect = AppError(
            code="NOT_FOUND",
            message="Connector install not found for tenant",
            status_code=404,
        )

        response = client.post(
            "/api/v1/founder/integration-command/sync-jobs",
            json={
                "tenant_connector_install_id": str(install_id),
                "direction": "OUTBOUND",
            },
        )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert db_stub.commit_calls == 0


def test_add_dead_letter_success_commits_and_scopes_tenant() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    sync_job_id = uuid.uuid4()
    db_stub = _DBStub()
    client = _build_client(
        db_stub,
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="founder"),
    )

    created = datetime.now(UTC)
    dead_letter = _DeadLetterModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connector_sync_job_id=sync_job_id,
        external_record_ref="external-123",
        reason="payload mismatch",
        payload={"field": "value"},
        created_at=created,
        updated_at=created,
    )

    with patch("core_app.api.founder_integration_command_router.FounderCommandDomainService") as svc_cls:
        svc = svc_cls.return_value
        svc.add_sync_dead_letter.return_value = dead_letter

        response = client.post(
            f"/api/v1/founder/integration-command/sync-jobs/{sync_job_id}/dead-letters",
            json={
                "external_record_ref": "external-123",
                "reason": "payload mismatch",
                "payload": {"field": "value"},
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["external_record_ref"] == "external-123"

    svc.add_sync_dead_letter.assert_called_once_with(
        tenant_id=tenant_id,
        actor_user_id=user_id,
        connector_sync_job_id=sync_job_id,
        external_record_ref="external-123",
        reason="payload mismatch",
        payload={"field": "value"},
    )
    assert db_stub.commit_calls == 1
    assert db_stub.refreshed == [dead_letter]


def test_write_endpoints_require_founder_role() -> None:
    tenant_id = uuid.uuid4()
    db_stub = _DBStub()
    client = _build_client(
        db_stub,
        CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, role="viewer"),
    )

    install_id = uuid.uuid4()
    response = client.post(
        "/api/v1/founder/integration-command/sync-jobs",
        json={
            "tenant_connector_install_id": str(install_id),
            "direction": "OUTBOUND",
        },
    )

    assert response.status_code == 403
