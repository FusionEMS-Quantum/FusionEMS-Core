"""Integration tests for the Telnyx fax webhook endpoint.

These tests validate current router behavior at /api/v1/webhooks/telnyx/fax with
explicit signature and idempotency handling.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api import fax_webhook_router


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    # Default query shape used by tenant resolution helpers.
    db.execute.return_value = SimpleNamespace(fetchone=lambda: None)
    return db


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, mock_db: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(fax_webhook_router.router)
    app.dependency_overrides[fax_webhook_router.db_session_dependency] = lambda: mock_db

    monkeypatch.setattr(
        fax_webhook_router,
        "get_settings",
        lambda: SimpleNamespace(
            telnyx_public_key="test-public-key",
            telnyx_webhook_tolerance_seconds=300,
            telnyx_api_key="",
            s3_bucket_docs="",
            fax_classify_queue_url="",
        ),
    )
    return TestClient(app)


def _payload(*, event_type: str = "fax.received", event_id: str = "evt-1") -> dict:
    return {
        "data": {
            "id": event_id,
            "event_type": event_type,
            "payload": {
                "id": "fax-1",
                "fax_id": "fax-1",
                "from": "+14155552671",
                "to": "+18005551234",
                "media_url": "",
            },
        }
    }


def test_rejects_invalid_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fax_webhook_router, "verify_telnyx_webhook", lambda **_: False)

    response = client.post("/api/v1/webhooks/telnyx/fax", json=_payload())

    assert response.status_code == 400
    assert response.json().get("detail") == "invalid_telnyx_signature"


def test_rejects_invalid_json_when_signature_valid(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fax_webhook_router, "verify_telnyx_webhook", lambda **_: True)

    response = client.post(
        "/api/v1/webhooks/telnyx/fax",
        data="{invalid",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json().get("detail") == "invalid_json"


def test_duplicate_event_short_circuits(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fax_webhook_router, "verify_telnyx_webhook", lambda **_: True)
    monkeypatch.setattr(fax_webhook_router, "_ensure_event_receipt", lambda *_, **__: False)

    response = client.post("/api/v1/webhooks/telnyx/fax", json=_payload(event_id="evt-dup"))

    assert response.status_code == 200
    assert response.json() == {"status": "duplicate"}


def test_non_received_event_without_tenant_is_ignored(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mark_processed = MagicMock()

    monkeypatch.setattr(fax_webhook_router, "verify_telnyx_webhook", lambda **_: True)
    monkeypatch.setattr(fax_webhook_router, "_ensure_event_receipt", lambda *_, **__: True)
    monkeypatch.setattr(fax_webhook_router, "_resolve_tenant_by_did", lambda *_, **__: None)
    monkeypatch.setattr(fax_webhook_router, "_mark_event_processed", mark_processed)

    response = client.post("/api/v1/webhooks/telnyx/fax", json=_payload(event_type="fax.unknown"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["detail"] == "non_received_event_ignored"
    mark_processed.assert_called_once()


def test_received_event_without_tenant_skips_persistence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mark_processed = MagicMock()

    monkeypatch.setattr(fax_webhook_router, "verify_telnyx_webhook", lambda **_: True)
    monkeypatch.setattr(fax_webhook_router, "_ensure_event_receipt", lambda *_, **__: True)
    monkeypatch.setattr(fax_webhook_router, "_resolve_tenant_by_did", lambda *_, **__: None)
    monkeypatch.setattr(fax_webhook_router, "_mark_event_processed", mark_processed)

    response = client.post("/api/v1/webhooks/telnyx/fax", json=_payload(event_type="fax.received"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["detail"] == "tenant_not_resolved"
    mark_processed.assert_called_once()
