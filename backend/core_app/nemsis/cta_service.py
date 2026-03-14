from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core_app.core.config import get_settings
from core_app.nemsis.cta_cases import (
    CTATestCase,
    generate_cta_case_xml,
    get_cta_case,
    list_cta_cases,
)
from core_app.nemsis.cta_soap_client import (
    CTACredentials,
    NEMSISCTASoapClient,
    normalize_cta_state,
    translate_cta_code,
)
from core_app.nemsis.validator import NEMSISValidator
from core_app.schemas.auth import CurrentUser

if TYPE_CHECKING:
    from core_app.services.domination_service import DominationService


@dataclass(frozen=True)
class CTAExecutionCredentials:
    username: str
    password: str
    organization: str
    endpoint_url: str


class CTATestRunService:
    def __init__(self, db: Session, svc: DominationService) -> None:
        self._db = db
        self._svc = svc
        self._validator = NEMSISValidator()

    def list_cases(self) -> list[dict[str, Any]]:
        return [self._serialize_case(case) for case in list_cta_cases()]

    def list_runs(self, tenant_id: str) -> list[dict[str, Any]]:
        rows = self._svc.repo("nemsis_export_jobs").list(tenant_id=tenant_id, limit=100)
        filtered = [row for row in rows if (row.get("data") or {}).get("job_kind") == "cta_test_run"]
        return [self._serialize_run(row) for row in filtered]

    def get_run(self, tenant_id: str, run_id: str) -> dict[str, Any]:
        row = self._svc.repo("nemsis_export_jobs").get(tenant_id=tenant_id, record_id=uuid.UUID(run_id))
        if row is None or (row.get("data") or {}).get("job_kind") != "cta_test_run":
            raise HTTPException(status_code=404, detail="CTA test run not found")
        return self._serialize_run(row)

    async def run_case(
        self,
        *,
        payload: dict[str, Any],
        current: CurrentUser,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        case = get_cta_case(str(payload.get("case_id", "")))
        credentials = self._resolve_credentials(payload)
        dem_reference = self._latest_dem_reference_xml(current.tenant_id) if case.dataset_type == "EMS" else None
        artifact = generate_cta_case_xml(case, reference_dem_xml=dem_reference)
        validation = self._validator.validate_xml_bytes(artifact.xml_bytes, state_code="FL")
        blocking_issues = [issue.to_dict() for issue in validation.issues if issue.severity == "error"]
        unresolved = list(artifact.unresolved_placeholders)
        run_record = await self._create_run_record(
            current=current,
            case=case,
            artifact=artifact,
            validation=validation.to_dict(),
            credentials=credentials,
            correlation_id=correlation_id,
        )

        if unresolved:
            return await self._finalize_failure(
                run_record=run_record,
                current=current,
                correlation_id=correlation_id,
                summary="Failed before submission: vendor placeholders are still unresolved.",
                submit_status_code=None,
                retrieve_status_code=None,
                extra_updates={"unresolved_placeholders": unresolved},
            )

        if blocking_issues:
            return await self._finalize_failure(
                run_record=run_record,
                current=current,
                correlation_id=correlation_id,
                summary="Failed before submission: local validation found blocking issues.",
                submit_status_code=None,
                retrieve_status_code=None,
                extra_updates={"blocking_issues": blocking_issues},
            )

        validated_record = await self._update_run(
            run_record=run_record,
            current=current,
            correlation_id=correlation_id,
            patch_data={
                "status": "validated",
                "plain_summary": "Ready for CTA submission.",
            },
        )

        client = NEMSISCTASoapClient(endpoint_url=credentials.endpoint_url)
        limit_result = await client.query_limit(
            CTACredentials(
                username=credentials.username,
                password=credentials.password,
                organization=credentials.organization,
            )
        )
        if (
            limit_result.limit_kb is not None
            and limit_result.limit_kb > 0
            and artifact.xml_bytes
            and len(artifact.xml_bytes) > limit_result.limit_kb * 1024
        ):
            return await self._finalize_failure(
                run_record=validated_record,
                current=current,
                correlation_id=correlation_id,
                summary="Failed before submission: payload exceeds CTA size limit.",
                submit_status_code=limit_result.status_code,
                retrieve_status_code=None,
                extra_updates={
                    "query_limit_kb": limit_result.limit_kb,
                    "query_limit_request_xml": limit_result.sanitized_request_xml,
                    "query_limit_response_xml": limit_result.raw_response_xml,
                },
            )

        submit_result = await client.submit_data(
            CTACredentials(
                username=credentials.username,
                password=credentials.password,
                organization=credentials.organization,
            ),
            xml_bytes=artifact.xml_bytes,
            request_data_schema=case.request_data_schema,
            schema_version=case.schema_version,
            additional_info=str(payload.get("additional_info") or case.case_id),
        )

        state = normalize_cta_state(submit_result.status_code)
        summary = translate_cta_code(submit_result.status_code)
        if state == "pending":
            state = "submitted" if submit_result.request_handle else "pending"

        updated = await self._update_run(
            run_record=validated_record,
            current=current,
            correlation_id=correlation_id,
            patch_data={
                "status": state,
                "request_handle": submit_result.request_handle,
                "submit_status_code": submit_result.status_code,
                "plain_summary": summary,
                "query_limit_request_xml": limit_result.sanitized_request_xml,
                "query_limit_response_xml": limit_result.raw_response_xml,
                "query_limit_kb": limit_result.limit_kb,
                "submit_request_xml": submit_result.sanitized_request_xml,
                "submit_response_xml": submit_result.raw_response_xml,
                "last_checked_at": datetime.now(UTC).isoformat(),
            },
        )
        return self._serialize_run(updated)

    async def check_status(
        self,
        *,
        run_id: str,
        payload: dict[str, Any],
        current: CurrentUser,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        row = self._svc.repo("nemsis_export_jobs").get(tenant_id=current.tenant_id, record_id=uuid.UUID(run_id))
        if row is None or (row.get("data") or {}).get("job_kind") != "cta_test_run":
            raise HTTPException(status_code=404, detail="CTA test run not found")
        row_data = dict(row.get("data") or {})
        request_handle = str(row_data.get("request_handle") or "")
        if not request_handle:
            raise HTTPException(status_code=422, detail="CTA request handle not found for this run")
        credentials = self._resolve_credentials(payload)
        client = NEMSISCTASoapClient(endpoint_url=credentials.endpoint_url)
        result = await client.retrieve_status(
            CTACredentials(
                username=credentials.username,
                password=credentials.password,
                organization=credentials.organization,
            ),
            request_handle=request_handle,
            original_request_type="SubmitData",
            additional_info=str(payload.get("additional_info") or row_data.get("case_id") or ""),
        )
        state = normalize_cta_state(result.status_code)
        plain_summary = translate_cta_code(result.status_code)
        updated = await self._update_run(
            run_record=row,
            current=current,
            correlation_id=correlation_id,
            patch_data={
                "status": state,
                "retrieve_status_code": result.status_code,
                "plain_summary": plain_summary,
                "retrieve_request_xml": result.sanitized_request_xml,
                "retrieve_response_xml": result.raw_response_xml,
                "cta_reports": result.reports,
                "last_checked_at": datetime.now(UTC).isoformat(),
            },
        )
        return self._serialize_run(updated)

    async def _create_run_record(
        self,
        *,
        current: CurrentUser,
        case: CTATestCase,
        artifact: Any,
        validation: dict[str, Any],
        credentials: CTAExecutionCredentials,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        return await self._svc.create(
            table="nemsis_export_jobs",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "job_kind": "cta_test_run",
                "status": "draft",
                "case_id": case.case_id,
                "case_label": case.short_name,
                "case_description": case.description,
                "dataset_type": case.dataset_type,
                "request_data_schema": case.request_data_schema,
                "schema_version": case.schema_version,
                "organization": credentials.organization,
                "endpoint_url": credentials.endpoint_url,
                "xml_sha256": artifact.xml_sha256,
                "xml_b64": base64.b64encode(artifact.xml_bytes).decode("utf-8"),
                "xml_size_bytes": len(artifact.xml_bytes),
                "resolved_test_key": artifact.resolved_test_key,
                "plain_summary": "XML generated. Local validation in progress.",
                "validation": validation,
                "warnings": list(artifact.warnings),
                "created_at": now,
                "updated_at": now,
                "last_checked_at": None,
            },
            correlation_id=correlation_id,
        )

    async def _finalize_failure(
        self,
        *,
        run_record: dict[str, Any],
        current: CurrentUser,
        correlation_id: str | None,
        summary: str,
        submit_status_code: int | None,
        retrieve_status_code: int | None,
        extra_updates: dict[str, Any],
    ) -> dict[str, Any]:
        updated = await self._update_run(
            run_record=run_record,
            current=current,
            correlation_id=correlation_id,
            patch_data={
                "status": "failed",
                "plain_summary": summary,
                "submit_status_code": submit_status_code,
                "retrieve_status_code": retrieve_status_code,
                "last_checked_at": datetime.now(UTC).isoformat(),
                **extra_updates,
            },
        )
        return self._serialize_run(updated)

    async def _update_run(
        self,
        *,
        run_record: dict[str, Any],
        current: CurrentUser,
        correlation_id: str | None,
        patch_data: dict[str, Any],
    ) -> dict[str, Any]:
        row_data = dict(run_record.get("data") or {})
        history = list(row_data.get("history") or [])
        if patch_data.get("status") and patch_data.get("status") != row_data.get("status"):
            history.append(
                {
                    "status": patch_data.get("status"),
                    "at": datetime.now(UTC).isoformat(),
                    "summary": patch_data.get("plain_summary"),
                }
            )
        merged = {
            **row_data,
            **patch_data,
            "history": history,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        updated = await self._svc.update(
            table="nemsis_export_jobs",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(str(run_record["id"])),
            expected_version=int(run_record.get("version", 1)),
            patch={"data": merged},
            correlation_id=correlation_id,
        )
        if updated is None:
            raise HTTPException(status_code=409, detail="CTA run was updated by another request")
        return updated

    def _resolve_credentials(self, payload: dict[str, Any]) -> CTAExecutionCredentials:
        settings = get_settings()
        raw_credentials = payload.get("credentials") if isinstance(payload.get("credentials"), dict) else {}
        username = str(raw_credentials.get("username") or settings.nemsis_cta_username or "").strip()
        password = str(raw_credentials.get("password") or settings.nemsis_cta_password or "").strip()
        organization = str(raw_credentials.get("organization") or settings.nemsis_cta_organization or "").strip()
        endpoint_url = str(payload.get("endpoint_url") or settings.nemsis_cta_endpoint or "").strip()
        if not username or not password or not organization:
            raise HTTPException(
                status_code=422,
                detail="CTA username, password, and organization are required before submission.",
            )
        if not endpoint_url:
            raise HTTPException(status_code=422, detail="CTA endpoint URL is required before submission.")
        return CTAExecutionCredentials(
            username=username,
            password=password,
            organization=organization,
            endpoint_url=endpoint_url,
        )

    def _latest_dem_reference_xml(self, tenant_id: str) -> bytes | None:
        rows = self._svc.repo("nemsis_export_jobs").list(tenant_id=tenant_id, limit=100)
        for row in rows:
            data = row.get("data") or {}
            if data.get("job_kind") != "cta_test_run":
                continue
            if data.get("dataset_type") != "DEM":
                continue
            xml_b64 = data.get("xml_b64")
            if isinstance(xml_b64, str) and xml_b64:
                try:
                    return base64.b64decode(xml_b64)
                except Exception:
                    return None
        return None

    def _serialize_case(self, case: CTATestCase) -> dict[str, Any]:
        return {
            "case_id": case.case_id,
            "short_name": case.short_name,
            "description": case.description,
            "dataset_type": case.dataset_type,
            "expected_result": case.expected_result,
            "schema_version": case.schema_version,
            "request_data_schema": case.request_data_schema,
            "test_key_element": case.test_key_element,
        }

    def _serialize_run(self, row: dict[str, Any]) -> dict[str, Any]:
        data = dict(row.get("data") or {})
        validation = data.get("validation") or {}
        issues = validation.get("issues") if isinstance(validation, dict) else []
        blocking_count = len([issue for issue in issues if issue.get("severity") == "error"]) if isinstance(issues, list) else 0
        return {
            "id": str(row["id"]),
            "status": data.get("status", "draft"),
            "case_id": data.get("case_id"),
            "case_label": data.get("case_label"),
            "dataset_type": data.get("dataset_type"),
            "schema_version": data.get("schema_version"),
            "request_data_schema": data.get("request_data_schema"),
            "request_handle": data.get("request_handle"),
            "submit_status_code": data.get("submit_status_code"),
            "retrieve_status_code": data.get("retrieve_status_code"),
            "plain_summary": data.get("plain_summary"),
            "current_state_label": _state_label(str(data.get("status", "draft")), data.get("submit_status_code"), data.get("retrieve_status_code")),
            "validation_blocking_count": blocking_count,
            "resolved_test_key": data.get("resolved_test_key"),
            "organization": data.get("organization"),
            "last_checked_at": data.get("last_checked_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "history": data.get("history", []),
            "details": {
                "validation": validation,
                "warnings": data.get("warnings", []),
                "cta_reports": data.get("cta_reports", {}),
                "query_limit_kb": data.get("query_limit_kb"),
                "query_limit_request_xml": data.get("query_limit_request_xml"),
                "query_limit_response_xml": data.get("query_limit_response_xml"),
                "submit_request_xml": data.get("submit_request_xml"),
                "submit_response_xml": data.get("submit_response_xml"),
                "retrieve_request_xml": data.get("retrieve_request_xml"),
                "retrieve_response_xml": data.get("retrieve_response_xml"),
                "xml_b64": data.get("xml_b64"),
                "xml_sha256": data.get("xml_sha256"),
            },
        }


def _state_label(status: str, submit_code: Any, retrieve_code: Any) -> str:
    code = retrieve_code if retrieve_code is not None else submit_code
    if status == "draft":
        return "Ready"
    if status == "validated":
        return "Ready"
    if status == "submitted":
        return "Submitted"
    if status == "pending":
        return "Waiting on NEMSIS"
    if status == "passed":
        return "Passed"
    if status == "passed_with_warnings":
        return "Passed with Warnings"
    if isinstance(code, int):
        return translate_cta_code(code)
    return "Failed"
