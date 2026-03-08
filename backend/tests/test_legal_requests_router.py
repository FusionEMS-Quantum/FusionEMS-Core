from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.api.legal_requests_router import router
from core_app.core.errors import AppError
from core_app.models.legal_requests import LegalRequestStatus, LegalRequestType
from core_app.schemas.auth import CurrentUser


@dataclass
class _DBStub:
    commit_calls: int = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def refresh(self, _obj: object) -> None:
        return None


@dataclass
class _RequestRow:
    id: uuid.UUID
    status: LegalRequestStatus
    request_type: LegalRequestType
    workflow_state: str = "request_received"
    payment_status: str = "not_required"
    payment_required: bool = False
    margin_status: str = "manual_review_required"
    fee_quote: dict[str, object] | None = None


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


def test_create_legal_request_intake_success() -> None:
    db_stub = _DBStub()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="founder")
    client = _build_client(db_stub=db_stub, current_user=current)

    req_id = uuid.uuid4()
    fake_row = _RequestRow(
        id=req_id,
        status=LegalRequestStatus.MISSING_DOCS,
        request_type=LegalRequestType.HIPAA_ROI,
    )

    with patch("core_app.api.legal_requests_router.LegalRequestsService") as svc_cls:
        svc = svc_cls.return_value
        svc.system_tenant_id.return_value = uuid.UUID("00000000-0000-0000-0000-000000000001")
        svc.create_intake.return_value = (
            fake_row,
            "intake-token-1234567890",
            {
                "classification": "hipaa_roi",
                "classification_confidence": 0.9,
                "likely_invalid_or_incomplete": True,
                "urgency_level": "normal",
                "deadline_risk": "watch",
                "mismatch_signals": [],
                "rationale": "deterministic fallback",
            },
            [
                {
                    "code": "missing_authorization",
                    "title": "No valid authorization",
                    "detail": "Authorization required",
                    "severity": "high",
                }
            ],
            [
                {
                    "code": "authorization",
                    "label": "Valid HIPAA authorization",
                    "required": True,
                    "satisfied": False,
                }
            ],
        )

        response = client.post(
            "/api/v1/legal-requests/intake",
            json={
                "request_type": "hipaa_roi",
                "requesting_party": "patient",
                "requester_name": "Jane Doe",
                "request_documents": [],
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["request_id"] == str(req_id)
    assert body["status"] == "missing_docs"
    assert body["request_type"] == "hipaa_roi"
    assert db_stub.commit_calls == 1


def test_founder_queue_requires_authorized_role() -> None:
    db_stub = _DBStub()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="viewer")
    client = _build_client(db_stub=db_stub, current_user=current)

    response = client.get("/api/v1/legal-requests/founder/queue")
    assert response.status_code == 403


def test_consume_delivery_link_wiring() -> None:
    db_stub = _DBStub()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="founder")
    client = _build_client(db_stub=db_stub, current_user=current)

    with patch("core_app.api.legal_requests_router.LegalRequestsService") as svc_cls:
        svc = svc_cls.return_value
        svc.consume_delivery_link.return_value = {
            "request_id": str(uuid.uuid4()),
            "status": "delivered",
            "packet_manifest": {"response_packet_uri": "inline://x"},
            "redaction_mode": "court_safe_minimum_necessary",
        }

        response = client.get("/api/v1/legal-requests/delivery/token-abc-123")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "delivered"
    assert db_stub.commit_calls == 1


def test_preview_quote_wiring() -> None:
    db_stub = _DBStub()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="founder")
    client = _build_client(db_stub=db_stub, current_user=current)

    request_id = uuid.uuid4()

    with patch("core_app.api.legal_requests_router.LegalRequestsService") as svc_cls:
        svc = svc_cls.return_value
        svc.system_tenant_id.return_value = uuid.UUID("00000000-0000-0000-0000-000000000001")
        svc.preview_quote.return_value = {
            "request_id": str(request_id),
            "currency": "usd",
            "total_due_cents": 4200,
            "agency_payout_cents": 3780,
            "platform_fee_cents": 420,
            "margin_status": "profitable",
            "payment_required": True,
            "workflow_state": "payment_required",
            "requester_category": "attorney",
            "delivery_mode": "secure_digital",
            "line_items": [],
            "costs": {
                "estimated_processor_fee_cents": 151,
                "estimated_labor_cost_cents": 600,
                "estimated_lob_cost_cents": 0,
                "estimated_platform_margin_cents": 269,
            },
            "hold_reasons": ["Fulfillment remains on hold until required payment clears."],
        }

        response = client.post(
            f"/api/v1/legal-requests/{request_id}/pricing/quote",
            json={"intake_token": "intake-token-1234567890"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_state"] == "payment_required"
    assert db_stub.commit_calls == 1


def test_create_legal_payment_checkout_wiring() -> None:
    db_stub = _DBStub()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="founder")
    client = _build_client(db_stub=db_stub, current_user=current)

    request_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    with patch("core_app.api.legal_requests_router.LegalRequestsService") as svc_cls:
        svc = svc_cls.return_value
        svc.system_tenant_id.return_value = uuid.UUID("00000000-0000-0000-0000-000000000001")
        svc.create_payment_checkout.return_value = {
            "request_id": str(request_id),
            "payment_id": str(payment_id),
            "payment_status": "payment_link_created",
            "workflow_state": "payment_link_created",
            "checkout_url": "https://checkout.stripe.com/x",
            "checkout_session_id": "cs_test_123",
            "connected_account_id": "acct_123",
            "amount_due_cents": 9900,
            "agency_payout_cents": 8910,
            "platform_fee_cents": 990,
        }

        response = client.post(
            f"/api/v1/legal-requests/{request_id}/payment/checkout",
            json={"intake_token": "intake-token-1234567890"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["checkout_session_id"] == "cs_test_123"
    assert db_stub.commit_calls == 1
