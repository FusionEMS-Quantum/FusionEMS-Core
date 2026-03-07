from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.compliance.nemsis_xml_generator import (
    build_nemsis_document,
    validate_nemsis_xml,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/nemsis", tags=["NEMSIS"])


@router.post("/validate")
async def validate(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    result: dict[str, Any] = {"status": "queued", "input": payload}

    if payload.get("incident") and payload.get("patient"):
        xml_bytes = build_nemsis_document(
            incident=payload["incident"],
            patient=payload["patient"],
            vitals=payload.get("vitals", []),
            agency_info=payload.get("agency", {}),
        )
        validation = validate_nemsis_xml(xml_bytes)
        result = {
            "status": "validated" if validation["valid"] else "invalid",
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }

    return await svc.create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=result,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/exports")
async def create_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())

    xml_b64: str | None = None
    generation_error: str | None = None

    incident = payload.get("incident")
    patient = payload.get("patient")

    if incident and patient:
        try:
            xml_bytes = build_nemsis_document(
                incident=incident,
                patient=patient,
                vitals=payload.get("vitals", []),
                agency_info=payload.get("agency", {}),
            )
            xml_b64 = base64.b64encode(xml_bytes).decode()
        except Exception as exc:
            generation_error = str(exc)

    job: dict[str, Any] = {
        "status": (
            "completed" if xml_b64 else ("failed" if generation_error else "queued")
        ),
        "range": payload.get("range"),
        "agency": payload.get("agency"),
        "xml_b64": xml_b64,
        "error": generation_error,
    }

    return await svc.create(
        table="nemsis_export_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=job,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("nemsis_export_jobs").get(
        tenant_id=current.tenant_id, record_id=job_id
    )
    if not rec:
        return {"error": "not_found"}

    xml_b64 = rec.get("data", {}).get("xml_b64")
    if not xml_b64:
        return {
            "error": "xml_not_available",
            "status": rec.get("data", {}).get("status"),
        }

    xml_bytes = base64.b64decode(xml_b64)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=nemsis_{job_id}.xml"},
    )


@router.get("/exports/{job_id}")
async def get_export(
    job_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("nemsis_export_jobs").get(
        tenant_id=current.tenant_id, record_id=job_id
    )
    if not rec:
        return {"error": "not_found"}
    data = rec.get("data", {})
    return {
        "id": str(job_id),
        "status": data.get("status"),
        "range": data.get("range"),
        "agency": data.get("agency"),
        "error": data.get("error"),
        "has_xml": bool(data.get("xml_b64")),
    }

@router.post("/validate_raw_xml")
async def validate_raw_xml(
    request: Request,
    current: CurrentUser = Depends(get_current_user)
):
    body = await request.body()
    validation = validate_nemsis_xml(body)
    
    # Format for the frontend UI
    issues = []
    for err in validation.get("errors", []):
        issues.append({
            "id": f"err-{uuid.uuid4()}",
            "path": err.get("element", "Unknown"),
            "message": err.get("message", "Validation error"),
            "level": "error",
            "ui_section": "XML Upload",
            "suggested_fix": err.get("message", "Check XML schema")
        })
    for warn in validation.get("warnings", []):
        issues.append({
            "id": f"warn-{uuid.uuid4()}",
            "path": warn.get("element", "Unknown"),
            "message": warn.get("message", "Validation warning"),
            "level": "warning",
            "ui_section": "XML Upload",
            "suggested_fix": warn.get("message", "Check XML schema")
        })
        
    return {
        "valid": validation["valid"],
        "issues": issues,
        "raw_errors": validation["errors"],
        "raw_warnings": validation["warnings"]
    }

@router.post("/simulate_wisconsin")
async def simulate_wisconsin(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
):
    svc = DominationService(db, get_event_publisher())
    
    # Generate 5 mock payloads
    jobs = []
    for i in range(5):
        job = {
            "status": "completed",
            "range": {
                "start": f"2026-03-01T0{i}:00:00Z",
                "end": f"2026-03-01T0{i+1}:00:00Z"
            },
            "agency": {"id": "WI-1029", "name": "Wisconsin Advanced EMS"},
            "xml_b64": base64.b64encode(b"<EMSDataSet><Record/></EMSDataSet>").decode(),
            "simulated": True,
            "rules_passed": 142
        }
        res = await svc.create(
            table="nemsis_export_jobs",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data=job,
            correlation_id=getattr(request.state, "correlation_id", None)
        )
        jobs.append(res)
        
    return {"status": "success", "jobs": jobs}
