from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.api.terminology_router import router
from core_app.core.errors import AppError
from core_app.schemas.auth import CurrentUser


class _DBStub:
    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None


def _build_client(*, current_user: CurrentUser) -> TestClient:
    app = FastAPI()

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response(trace_id=None))

    app.include_router(router)

    def _override_db():
        yield _DBStub()

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def test_list_code_systems_maps_response_models() -> None:
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="ems")
    client = _build_client(current_user=current)

    cs = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=current.tenant_id,
        system_uri="http://hl7.org/fhir/sid/icd-10-cm",
        system_version="2025",
        name="ICD-10-CM",
        publisher="CMS",
        status="active",
        is_external=True,
        metadata_blob={},
        version=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    with patch("core_app.api.terminology_router.TerminologyService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_code_systems.return_value = [cs]

        resp = client.get("/api/v1/terminology/code-systems")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["system_uri"] == "http://hl7.org/fhir/sid/icd-10-cm"


def test_upsert_code_system_forbidden_for_viewer() -> None:
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="viewer")
    client = _build_client(current_user=current)

    resp = client.put(
        "/api/v1/terminology/code-systems",
        json={
            "system_uri": "http://example",
            "system_version": "",
            "name": "Example",
            "publisher": None,
            "status": "active",
            "is_external": True,
            "metadata_blob": {},
        },
    )

    assert resp.status_code == 403


def test_external_rxnav_normalize_success() -> None:
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="ems")
    client = _build_client(current_user=current)

    with patch("core_app.integrations.rxnav.RxNavClient") as client_cls:
        c = client_cls.return_value
        c.approximate_term = AsyncMock(
            return_value=[
            SimpleNamespace(rxcui="123", score=99, name=None, extra={"term": "aspirin"})
            ]
        )
        c.rxcui_to_name = AsyncMock(return_value="Aspirin")

        resp = client.post(
            "/api/v1/terminology/external/rxnav/normalize",
            json={"name": "aspirin"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["rxnorm_cui"] == "123"
    assert body["normalized_name"] == "Aspirin"


def test_external_nih_invalid_table_rejected() -> None:
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="ems")
    client = _build_client(current_user=current)

    resp = client.post(
        "/api/v1/terminology/external/nih/bad-table!",
        json={"q": "foo", "limit": 10},
    )

    assert resp.status_code == 400
