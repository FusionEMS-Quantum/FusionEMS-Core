from __future__ import annotations

import uuid
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.api.founder_tax_router import tax_advisor_router
from core_app.schemas.auth import CurrentUser


@dataclass
class _DBStub:
    def execute(self, *_args: object, **_kwargs: object) -> _DBStub:
        return self

    def scalars(self) -> _DBStub:
        return self

    def all(self) -> list[object]:
        return []


def _build_client(role: str = "founder") -> TestClient:
    app = FastAPI()
    app.include_router(tax_advisor_router, prefix="/api")

    def _override_db() -> Generator[_DBStub, None, None]:
        yield _DBStub()

    current_user = CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=role,
    )

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def test_realtime_efile_tracking_returns_orchestrated_status() -> None:
    client = _build_client()

    class _OrchestratorStub:
        async def realtime_status(self) -> dict[str, object]:
            return {
                "irs_mef": {"status": "configured", "mode": "ats_testing"},
                "wi_dor": {"status": "configured", "mode": "sandbox"},
            }

    with patch("core_app.api.founder_tax_router.EfileOrchestrator", _OrchestratorStub):
        response = client.get("/api/quantum-founder/efile/realtime-status")

    assert response.status_code == 200
    body = response.json()
    assert body["irs_mef"]["status"] == "configured"
    assert body["wi_dor"]["mode"] == "sandbox"


def test_transmit_federal_estimated_assigns_correlation_id() -> None:
    client = _build_client()

    class _ResultStub:
        def to_dict(self) -> dict[str, object]:
            return {
                "status": "accepted",
                "confirmation_number": "IRS-ABC12345",
                "timestamp": "2026-03-15T00:00:00Z",
                "errors": [],
            }

    recorded: dict[str, object] = {}

    class _IRSClientStub:
        async def submit_1040es(self, **kwargs: object) -> _ResultStub:
            recorded.update(kwargs)
            return _ResultStub()

    with patch("core_app.api.founder_tax_router.IRSMeFClient", _IRSClientStub):
        response = client.post(
            "/api/quantum-founder/efile/transmit/federal-estimated",
            json={
                "tax_year": 2026,
                "quarter": 2,
                "filer_ssn": "123-45-6789",
                "first_name": "Alex",
                "last_name": "Founder",
                "payment_amount": 1250.55,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["confirmation_number"] == "IRS-ABC12345"
    assert recorded["tax_year"] == 2026
    assert recorded["quarter"] == 2
    assert recorded["payment_amount"] == 1250.55
    assert isinstance(recorded["correlation_id"], str)
    assert recorded["correlation_id"]


def test_transmit_wisconsin_assigns_correlation_id() -> None:
    client = _build_client()

    class _ResultStub:
        def to_dict(self) -> dict[str, object]:
            return {
                "status": "accepted",
                "confirmation_number": "WI-XYZ98765",
                "timestamp": "2026-03-15T00:00:00Z",
                "errors": [],
            }

    recorded: dict[str, object] = {}

    class _WIClientStub:
        async def transmit_wi_form1(self, **kwargs: object) -> _ResultStub:
            recorded.update(kwargs)
            return _ResultStub()

    with patch("core_app.api.founder_tax_router.WisconsinDORClient", _WIClientStub):
        response = client.post(
            "/api/quantum-founder/efile/transmit/wisconsin",
            json={
                "tax_year": 2026,
                "filer_ssn": "123-45-6789",
                "first_name": "Alex",
                "last_name": "Founder",
                "street": "123 Main St",
                "city": "Madison",
                "zip_code": "53703",
                "wi_adjusted_gross_income": 94000,
                "wi_exemptions": 700,
                "wi_credits": 100,
                "wi_withholding": 500,
                "net_taxable_income": 83000,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["confirmation_number"] == "WI-XYZ98765"
    assert recorded["tax_year"] == 2026
    assert recorded["address"]["state"] == "WI"
    assert isinstance(recorded["correlation_id"], str)
    assert recorded["correlation_id"]