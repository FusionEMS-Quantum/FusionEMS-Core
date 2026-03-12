from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api import fax_router
from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser


class _Result:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def fetchone(self) -> dict[str, Any] | None:
        return self.first()


@dataclass
class _DBStub:
    inbox_rows: list[dict[str, Any]]
    match_rows: list[dict[str, Any]]

    def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = str(stmt)
        if "set_config('app.tenant_id'" in sql:
            return _Result([])
        if "FROM fax_documents" in sql:
            return _Result(self.inbox_rows)
        if "FROM document_matches" in sql:
            return _Result(self.match_rows)
        raise AssertionError(f"Unexpected SQL in test stub: {sql}")

    def commit(self) -> None:
        return None


def _build_client(*, current_user: CurrentUser, db_stub: _DBStub) -> TestClient:
    app = FastAPI()
    app.include_router(fax_router.router)

    def _override_db():
        yield db_stub

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def test_fax_inbox_folder_inbox_enriches_match_state() -> None:
    tenant_id = uuid.uuid4()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, role="billing")

    db_stub = _DBStub(
        inbox_rows=[
            {
                "fax_id": "fax-123",
                "from_phone": "+14155552671",
                "to_phone": "+18005551234",
                "s3_key_original": "docs/fax-123.pdf",
                "sha256_original": "deadbeef",
                "status": "stored",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ],
        match_rows=[
            {
                "data": {
                    "fax_id": "fax-123",
                    "match_status": "review",
                    "suggested_matches": [
                        {"claim_id": "claim-1", "patient_name": "Jane Doe", "score": 0.73}
                    ],
                    "confidence": 0.73,
                    "match_type": "suggested",
                },
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ],
    )

    client = _build_client(current_user=current, db_stub=db_stub)

    resp = client.get("/api/v1/fax/inbox", params={"folder": "inbox", "limit": 10})
    assert resp.status_code == 200

    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["id"] == "fax-123"
    assert body[0]["document_match_status"] == "review"
    assert body[0]["data"]["match_suggestions"][0]["claim_id"] == "claim-1"


def test_match_trigger_rejects_outbound_uuid() -> None:
    tenant_id = uuid.uuid4()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, role="billing")

    db_stub = _DBStub(inbox_rows=[], match_rows=[])
    client = _build_client(current_user=current, db_stub=db_stub)

    outbound_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/fax/{outbound_id}/match/trigger")
    assert resp.status_code == 400
    assert resp.json().get("detail") == "outbound_fax_match_not_supported"


def test_match_trigger_accepts_inbound_string_without_body(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    current = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, role="billing")

    class _SvcStub:
        def __init__(self, _db: Any, _publisher: Any):
            return None

        async def create(self, **_: Any) -> dict[str, Any]:
            return {"id": "fax-event-1"}

    class _PublisherStub:
        def publish_sync(self, **_: Any) -> None:
            return None

    def _publisher_factory() -> _PublisherStub:
        return _PublisherStub()

    def _settings_factory() -> SimpleNamespace:
        return SimpleNamespace(fax_classify_queue_url="")

    monkeypatch.setattr(fax_router, "DominationService", _SvcStub)
    monkeypatch.setattr(fax_router, "get_event_publisher", _publisher_factory)
    monkeypatch.setattr(fax_router, "_resolve_fax_s3_location", lambda **_: None)
    monkeypatch.setattr(fax_router, "get_settings", _settings_factory)

    db_stub = _DBStub(inbox_rows=[], match_rows=[])
    client = _build_client(current_user=current, db_stub=db_stub)

    resp = client.post("/api/v1/fax/telnyx-fax-1/match/trigger")
    assert resp.status_code == 200
    assert resp.json()["status"] == "triggered"
    assert resp.json()["fax_event_id"] == "fax-event-1"
