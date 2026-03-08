from __future__ import annotations

import uuid
from typing import Any

import boto3
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.medical_necessity_engine import evaluate as evaluate_mn

router = APIRouter(prefix="/api/v1/transportlink", tags=["TransportLink"])


@router.post("/requests")
async def create_request(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="facility_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/requests")
async def list_requests(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    request_status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("facility_requests").list(
        tenant_id=current.tenant_id, limit=limit, offset=offset
    )
    # Apply in-memory filters when query params provided
    if request_status:
        items = [r for r in items if (r.get("data") or {}).get("status") == request_status]
    if priority:
        items = [r for r in items if (r.get("data") or {}).get("priority") == priority]
    return items


@router.get("/requests/{request_id}")
async def get_request(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("facility_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")
    return rec


@router.patch("/requests/{request_id}")
async def patch_request(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = await svc.update(
        table="facility_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=request_id,
        expected_version=int(payload.pop("expected_version", 0)),
        patch=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found or version conflict")
    return rec


@router.post("/requests/{request_id}/upload-url")
async def upload_url(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    _request: Request,
    current: CurrentUser = Depends(get_current_user),
    _db: Session = Depends(db_session_dependency),
):
    settings = get_settings()
    filename = str(payload.get("filename") or f"{request_id}.bin")
    s3_key = f"transportlink/{current.tenant_id}/{request_id}/{filename}"
    presigned_url = ""
    if settings.s3_bucket_docs:
        s3 = boto3.client("s3")
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket_docs,
                "Key": s3_key,
                "ContentType": payload.get("content_type")
                or "application/octet-stream",
            },
            ExpiresIn=900,
        )
    return {
        "request_id": str(request_id),
        "upload": {
            "method": "PUT",
            "url": presigned_url,
            "key": s3_key,
            "expires_in": 900,
        },
    }


@router.post("/requests/{request_id}/submit")
async def submit(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    _request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    patch = {"status": "submitted"}
    rec = svc.repo("facility_requests").update(
        tenant_id=current.tenant_id,
        record_id=request_id,
        expected_version=int(payload.get("expected_version", 0)),
        patch=patch,
    )
    return rec or {"error": "not_found"}


@router.get("/requests/{request_id}/status")
async def get_request_status(
    request_id: uuid.UUID,
    _request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("facility_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    return rec or {"error": "not_found"}


@router.get("/facilities/{facility_id}/schedule")
async def facility_schedule(
    facility_id: uuid.UUID,
    _request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("facility_requests").list(
        tenant_id=current.tenant_id, limit=500, offset=0
    )
    facility_id_str = str(facility_id)
    return [
        row
        for row in items
        if str((row.get("data") or {}).get("facility_id", "")) == facility_id_str
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CAD integration
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/requests/{request_id}/submit-to-cad")
async def submit_to_cad(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Transition a validated transport request to CAD status.
    Performs a final readiness check before allowing the transition.
    """
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("facility_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")

    data: dict[str, Any] = rec.get("data") or {}

    # Hard-stop readiness checks
    failures: list[str] = []
    if not data.get("patient_last") and not data.get("patient_name"):
        failures.append("Patient name is required")
    if not data.get("origin_address") and not data.get("origin_facility"):
        failures.append("Origin is required")
    if not data.get("destination_address") and not data.get("destination_facility"):
        failures.append("Destination is required")
    if not data.get("requested_service_level"):
        failures.append("Service level is required")
    if not data.get("pcs_complete"):
        failures.append("PCS must be complete before CAD submission")
    if not data.get("aob_complete"):
        failures.append("AOB must be complete before CAD submission")
    if not data.get("facesheet_uploaded"):
        failures.append("Facesheet must be uploaded before CAD submission")

    # Check medical necessity
    mn_status = data.get("medical_necessity_status", "")
    if mn_status in ("LIKELY_NOT_MEDICALLY_NECESSARY", "MEDICAL_NECESSITY_INSUFFICIENT"):
        failures.append(
            f"Medical necessity status '{mn_status}' does not support CAD submission. "
            "Resolve documentation before proceeding."
        )

    if failures:
        raise HTTPException(
            status_code=422,
            detail={"message": "Request is not ready for CAD submission", "failures": failures},
        )

    corr_id = getattr(request.state, "correlation_id", None)
    rec = await svc.update(
        table="facility_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=request_id,
        expected_version=int(payload.get("expected_version", rec.get("version", 0))),
        patch={"status": "sent_to_cad"},
        correlation_id=corr_id,
    )
    return rec or {"error": "update_failed"}


# ─────────────────────────────────────────────────────────────────────────────
# Medical necessity evaluation
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/requests/{request_id}/evaluate-mn")
async def evaluate_medical_necessity(
    request_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Run server-side medical necessity evaluation and persist the result
    back into the request data blob.
    """
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("facility_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")

    data: dict[str, Any] = rec.get("data") or {}
    result = evaluate_mn(data)

    corr_id = getattr(request.state, "correlation_id", None)
    await svc.update(
        table="facility_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=request_id,
        expected_version=int(rec.get("version", 0)),
        patch={
            "medical_necessity_status": result.status.value,
            "medical_necessity_explanation": result.explanation,
            "medical_necessity_policy": result.policy,
            "abn_needed": result.abn_required,
        },
        correlation_id=corr_id,
    )

    return {
        "request_id": str(request_id),
        "status": result.status.value,
        "explanation": result.explanation,
        "policy": result.policy,
        "abn_required": result.abn_required,
        "findings": [
            {
                "rule_id": f.rule_id,
                "description": f.description,
                "policy_reference": f.policy_reference,
                "passed": f.passed,
                "detail": f.detail,
            }
            for f in result.findings
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Access requests (facility onboarding)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/access-requests")
async def create_access_request(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    """
    Public endpoint — no authentication required.
    Stores a facility portal access request for review by ops staff.
    """
    svc = DominationService(db, get_event_publisher())

    # Basic input validation
    required = ["facility_name", "requestor_name", "work_email"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HTTPException(status_code=422, detail={"missing_fields": missing})

    # Use a fixed "system" tenant UUID for unauthenticated submissions
    system_tenant = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return await svc.create(
        table="facility_access_requests",
        tenant_id=system_tenant,
        actor_user_id=None,
        data={**payload, "status": "pending"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Documents / OCR — presigned upload URL already exists above.
# Placeholder endpoints for OCR processing and field application.
# Full OCR pipeline requires a separate async worker (see core_app/worker.py).
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/documents")
async def list_documents(
    request_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("request_documents").list(
        tenant_id=current.tenant_id, limit=limit, offset=offset
    )
    if request_id:
        items = [r for r in items if str((r.get("data") or {}).get("request_id")) == str(request_id)]
    return items


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("request_documents").get(
        tenant_id=current.tenant_id, record_id=document_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Document not found")
    await svc.update(
        table="request_documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=document_id,
        expected_version=int(rec.get("version", 0)),
        patch={"status": "deleted"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"deleted": True}


@router.post("/documents/{document_id}/process-ocr")
async def trigger_ocr(
    document_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Enqueue OCR processing for an uploaded document."""
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("request_documents").get(
        tenant_id=current.tenant_id, record_id=document_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Document not found")
    # In production this publishes an event picked up by the async OCR worker.
    # The worker calls Textract / Google Document AI and writes results back.
    return {"queued": True, "document_id": str(document_id)}


@router.post("/documents/{document_id}/apply-ocr")
async def apply_ocr_fields(
    document_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Apply human-confirmed OCR fields to the linked transport request.
    Only confirmed fields (never raw OCR) are written.
    """
    confirmed_fields: dict[str, Any] = payload.get("confirmed_fields") or {}
    target_request_id_raw = payload.get("request_id")
    if not target_request_id_raw:
        raise HTTPException(status_code=422, detail="request_id is required")

    try:
        target_request_id = uuid.UUID(str(target_request_id_raw))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid request_id") from exc

    svc = DominationService(db, get_event_publisher())
    document = svc.repo("request_documents").get(
        tenant_id=current.tenant_id, record_id=document_id
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    rec = svc.repo("facility_requests").get(
        tenant_id=current.tenant_id, record_id=target_request_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Transport request not found")

    existing_data: dict[str, Any] = dict(rec.get("data") or {})
    corr_id = getattr(request.state, "correlation_id", None)

    # Merge only — do NOT overwrite fields that have already been confirmed by a human user.
    # Fields marked confirmed in the request data are not overwritten.
    protected_keys: set[str] = set((existing_data.get("_confirmed_fields") or {}).keys())
    patch_data: dict[str, Any] = {}
    for key, value in confirmed_fields.items():
        if key not in protected_keys:
            patch_data[key] = value

    if not patch_data:
        return {"applied": 0, "skipped": len(confirmed_fields)}

    await svc.update(
        table="facility_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=target_request_id,
        expected_version=int(rec.get("version", 0)),
        patch=patch_data,
        correlation_id=corr_id,
    )

    return {"applied": len(patch_data), "skipped": len(confirmed_fields) - len(patch_data)}
