from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core_app.nemsis import cta_service as cta_service_module
from core_app.nemsis.cta_cases import CTATestCase, CTAXmlArtifact
from core_app.nemsis.cta_service import CTATestRunService


@dataclass(frozen=True)
class _FakeValidationIssue:
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "plain_message": "problem"}


@dataclass(frozen=True)
class _FakeValidationResult:
    valid: bool
    issues: list[_FakeValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "issues": [issue.to_dict() for issue in self.issues]}


class _FakeRepo:
    def __init__(self, store: dict[str, list[dict[str, Any]]], table: str) -> None:
        self._store = store
        self._table = table

    def list(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = [row for row in self._store.get(self._table, []) if row["tenant_id"] == tenant_id]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return rows[:limit]

    def get(self, tenant_id: str, record_id: uuid.UUID) -> dict[str, Any] | None:
        for row in self._store.get(self._table, []):
            if row["tenant_id"] == tenant_id and row["id"] == record_id:
                return row
        return None


class _FakeDominationService:
    def __init__(self) -> None:
        self.store: dict[str, list[dict[str, Any]]] = {"nemsis_export_jobs": []}

    def repo(self, table: str) -> _FakeRepo:
        return _FakeRepo(self.store, table)

    async def create(
        self,
        *,
        table: str,
        tenant_id: str,
        actor_user_id: str,
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> dict[str, Any]:
        del actor_user_id, correlation_id
        row = {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "data": data,
            "version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.store.setdefault(table, []).append(row)
        return row

    async def update(
        self,
        *,
        table: str,
        tenant_id: str,
        actor_user_id: str,
        record_id: uuid.UUID,
        expected_version: int,
        patch: dict[str, Any],
        correlation_id: str | None,
    ) -> dict[str, Any] | None:
        del actor_user_id, correlation_id
        for row in self.store.get(table, []):
            if row["tenant_id"] != tenant_id or row["id"] != record_id:
                continue
            if row["version"] != expected_version:
                return None
            if "data" in patch:
                row["data"] = patch["data"]
            else:
                row["data"] = {**row["data"], **patch}
            row["version"] += 1
            row["updated_at"] = datetime.now(UTC).isoformat()
            return row
        return None


class _FakeSoapClient:
    async def query_limit(self, credentials: Any) -> Any:
        del credentials
        return SimpleNamespace(
            status_code=1,
            limit_kb=512,
            message="ok",
            raw_response_xml="<QueryLimitResponse/>",
            sanitized_request_xml="<QueryLimitRequest/>",
        )

    async def submit_data(self, credentials: Any, **kwargs: Any) -> Any:
        del credentials, kwargs
        return SimpleNamespace(
            status_code=10,
            request_handle="handle-001",
            message="Waiting on NEMSIS",
            raw_response_xml="<SubmitDataResponse/>",
            sanitized_request_xml="<SubmitDataRequest/>",
        )

    async def retrieve_status(self, credentials: Any, **kwargs: Any) -> Any:
        del credentials, kwargs
        return SimpleNamespace(
            status_code=1,
            request_handle="handle-001",
            message="Passed",
            reports={"xmlValidationReport": ["<report />"]},
            raw_response_xml="<RetrieveStatusResponse/>",
            sanitized_request_xml="<RetrieveStatusRequest/>",
        )


def _test_case(dataset_type: str = "DEM") -> CTATestCase:
    return CTATestCase(
        case_id="2025-DEM-1-FullSet_v351" if dataset_type == "DEM" else "2025-EMS-1-Allergy_v351",
        short_name="DEM 1",
        description="Demo case",
        dataset_type=dataset_type,  # type: ignore[arg-type]
        expected_result="PASS",
        schema_version="3.5.1",
        request_data_schema=62 if dataset_type == "DEM" else 61,
        html_path=Path("/tmp/fake-case.html"),
        test_key_element="dAgency.02" if dataset_type == "DEM" else "eResponse.04",
    )


def _test_artifact(case: CTATestCase, unresolved: tuple[str, ...] = ()) -> CTAXmlArtifact:
    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?><DEMDataSet xmlns="http://www.nemsis.org"><DemographicReport><dAgency><dAgency.02>351-T0495</dAgency.02></dAgency></DemographicReport></DEMDataSet>'
    return CTAXmlArtifact(
        case=case,
        xml_bytes=xml_bytes,
        xml_sha256="abc123",
        unresolved_placeholders=unresolved,
        warnings=(),
        resolved_test_key="351-T0495",
    )


@pytest.mark.asyncio
async def test_run_case_stops_when_vendor_placeholders_remain(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_svc = _FakeDominationService()
    service = CTATestRunService(db=SimpleNamespace(), svc=fake_svc)  # type: ignore[arg-type]
    service._validator = SimpleNamespace(validate_xml_bytes=lambda xml_bytes, state_code: _FakeValidationResult(valid=True, issues=[]))
    monkeypatch.setattr(cta_service_module, "get_cta_case", lambda case_id: _test_case())
    monkeypatch.setattr(cta_service_module, "generate_cta_case_xml", lambda case, reference_dem_xml=None: _test_artifact(case, unresolved=("dAgency.03:state_dataset",)))

    result = await service.run_case(
        payload={
            "case_id": "2025-DEM-1-FullSet_v351",
            "endpoint_url": "https://example.test",
            "credentials": {"username": "user", "password": "pass", "organization": "org"},
        },
        current=SimpleNamespace(tenant_id="tenant-1", user_id="user-1"),
        correlation_id="corr-1",
    )

    assert result["status"] == "failed"
    assert "vendor placeholders" in result["plain_summary"].lower()


@pytest.mark.asyncio
async def test_run_case_persists_request_handle_after_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_svc = _FakeDominationService()
    service = CTATestRunService(db=SimpleNamespace(), svc=fake_svc)  # type: ignore[arg-type]
    service._validator = SimpleNamespace(validate_xml_bytes=lambda xml_bytes, state_code: _FakeValidationResult(valid=True, issues=[]))
    monkeypatch.setattr(cta_service_module, "get_cta_case", lambda case_id: _test_case())
    monkeypatch.setattr(cta_service_module, "generate_cta_case_xml", lambda case, reference_dem_xml=None: _test_artifact(case))
    monkeypatch.setattr(cta_service_module, "NEMSISCTASoapClient", lambda endpoint_url=None: _FakeSoapClient())

    result = await service.run_case(
        payload={
            "case_id": "2025-DEM-1-FullSet_v351",
            "endpoint_url": "https://example.test",
            "credentials": {"username": "user", "password": "pass", "organization": "org"},
        },
        current=SimpleNamespace(tenant_id="tenant-1", user_id="user-1"),
        correlation_id="corr-2",
    )

    assert result["status"] == "submitted"
    assert result["request_handle"] == "handle-001"
    assert result["submit_status_code"] == 10
    stored_row = fake_svc.store["nemsis_export_jobs"][0]
    assert stored_row["data"]["request_handle"] == "handle-001"
    assert stored_row["data"]["status"] == "submitted"


@pytest.mark.asyncio
async def test_check_status_updates_run_to_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_svc = _FakeDominationService()
    service = CTATestRunService(db=SimpleNamespace(), svc=fake_svc)  # type: ignore[arg-type]
    created = await fake_svc.create(
        table="nemsis_export_jobs",
        tenant_id="tenant-1",
        actor_user_id="user-1",
        data={
            "job_kind": "cta_test_run",
            "status": "submitted",
            "case_id": "2025-DEM-1-FullSet_v351",
            "case_label": "DEM 1",
            "dataset_type": "DEM",
            "schema_version": "3.5.1",
            "request_data_schema": 62,
            "request_handle": "handle-001",
            "plain_summary": "Waiting on NEMSIS",
            "xml_b64": base64.b64encode(b"<xml/>").decode("utf-8"),
            "history": [],
        },
        correlation_id=None,
    )
    monkeypatch.setattr(cta_service_module, "NEMSISCTASoapClient", lambda endpoint_url=None: _FakeSoapClient())

    result = await service.check_status(
        run_id=str(created["id"]),
        payload={
            "endpoint_url": "https://example.test",
            "credentials": {"username": "user", "password": "pass", "organization": "org"},
        },
        current=SimpleNamespace(tenant_id="tenant-1", user_id="user-1"),
        correlation_id="corr-3",
    )

    assert result["status"] == "passed"
    assert result["retrieve_status_code"] == 1
    assert result["current_state_label"] == "Passed"


@pytest.mark.asyncio
async def test_run_case_stops_on_local_validation_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_svc = _FakeDominationService()
    service = CTATestRunService(db=SimpleNamespace(), svc=fake_svc)  # type: ignore[arg-type]
    service._validator = SimpleNamespace(
        validate_xml_bytes=lambda xml_bytes, state_code: _FakeValidationResult(valid=False, issues=[_FakeValidationIssue(severity="error")])
    )
    monkeypatch.setattr(cta_service_module, "get_cta_case", lambda case_id: _test_case())
    monkeypatch.setattr(cta_service_module, "generate_cta_case_xml", lambda case, reference_dem_xml=None: _test_artifact(case))

    result = await service.run_case(
        payload={
            "case_id": "2025-DEM-1-FullSet_v351",
            "endpoint_url": "https://example.test",
            "credentials": {"username": "user", "password": "pass", "organization": "org"},
        },
        current=SimpleNamespace(tenant_id="tenant-1", user_id="user-1"),
        correlation_id="corr-4",
    )

    assert result["status"] == "failed"
    assert "local validation" in result["plain_summary"].lower()
