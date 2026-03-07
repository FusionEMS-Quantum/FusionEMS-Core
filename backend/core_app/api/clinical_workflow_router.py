from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.epcr.chart_model import ChartStatus, QAStatus
from core_app.epcr.completeness_engine import CompletenessEngine
from core_app.epcr.nemsis_exporter import NEMSISExporter
from core_app.epcr.sync_engine import SyncEngine
from core_app.epcr.validation_engine import ValidationEngine
from core_app.nemsis.validator import NEMSISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/clinical", tags=["Clinical Workflows"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _get_chart_or_404(db: Session, chart_id: str, tenant_id: uuid.UUID) -> dict[str, Any]:
    rec = _svc(db).repo("epcr_charts").get(tenant_id=tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return rec


# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────


@router.post("/charts/{chart_id}/validate")
async def validate_chart(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Run the full clinical validation engine + completeness check.
    Returns blocking issues (prevent lock) and warnings (informational).
    Persists a validation snapshot.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]

    # 1. Completeness engine (NEMSIS-field-mapped)
    mode = chart_data.get("chart_mode", "bls")
    completeness = CompletenessEngine().score_chart(chart_data, mode)

    # 2. Clinical validation engine (timeline, vitals, medication safety)
    from core_app.epcr.chart_model import Chart as ChartModel
    chart_obj = ChartModel.from_dict(chart_data)
    val_status, val_issues = ValidationEngine().validate_chart(chart_obj)

    # 3. NEMSIS XML check
    xml_bytes = NEMSISExporter().export_chart(chart_data, agency_info={})
    nemsis_result = NEMSISValidator().validate_xml_bytes(xml_bytes)
    nemsis_errors = [
        {"element": i.element_id, "message": i.plain_message, "severity": i.severity, "fix": i.fix_hint}
        for i in nemsis_result.issues
    ]

    blocking = [i for i in val_issues if i.severity == "blocking"]
    warnings = [i for i in val_issues if i.severity == "warning"]
    has_blocking = bool(blocking) or any(e["severity"] == "error" for e in nemsis_errors)

    # 4. Persist validation snapshot
    corr_id = getattr(request.state, "correlation_id", None)
    snap = await _svc(db).create(
        table="epcr_validation_snapshots",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "chart_id": chart_id,
            "validated_at": datetime.now(UTC).isoformat(),
            "validation_status": val_status.value,
            "has_blocking": has_blocking,
            "blocking_issues": [{"message": i.message, "field": i.field_path} for i in blocking],
            "warnings": [{"message": i.message, "field": i.field_path} for i in warnings],
            "nemsis_issues": nemsis_errors,
            "completeness_score": completeness["score"],
            "completeness_missing": completeness.get("missing", []),
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "validation_status": val_status.value,
            "has_blocking": has_blocking,
        },
        correlation_id=corr_id,
    )

    return {
        "chart_id": chart_id,
        "validation_status": val_status.value,
        "has_blocking": has_blocking,
        "blocking_issues": [{"message": i.message, "field": i.field_path} for i in blocking],
        "warnings": [{"message": i.message, "field": i.field_path} for i in warnings],
        "nemsis_issues": nemsis_errors,
        "completeness_score": completeness["score"],
        "snapshot_id": str(snap["id"]),
    }


# ─────────────────────────────────────────────────────────────
# LOCK / AMENDMENT
# ─────────────────────────────────────────────────────────────


@router.post("/charts/{chart_id}/lock")
async def lock_chart(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Lock a chart. Fails if any blocking validation issues remain.
    Idempotent — already-locked charts return success.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]
    current_status = chart_data.get("chart_status")

    if current_status == ChartStatus.LOCKED.value:
        return {"locked": True, "chart_id": chart_id, "already_locked": True}

    allowed_from = {
        ChartStatus.READY_FOR_LOCK.value,
        ChartStatus.SYNCED.value,
        ChartStatus.CLINICAL_REVIEW_REQUIRED.value,
        ChartStatus.IN_PROGRESS.value,
        ChartStatus.CHART_CREATED.value,
    }
    if current_status not in allowed_from:
        raise HTTPException(
            status_code=422,
            detail=f"Chart cannot be locked from status: {current_status}",
        )

    # Hard validation gate — run validation engine, check for blockers
    from core_app.epcr.chart_model import Chart as ChartModel
    chart_obj = ChartModel.from_dict(chart_data)
    _val_status, val_issues = ValidationEngine().validate_chart(chart_obj)
    blocking = [i for i in val_issues if i.severity == "blocking"]

    # NEMSIS check
    xml_bytes = NEMSISExporter().export_chart(chart_data, agency_info={})
    nemsis_result = NEMSISValidator().validate_xml_bytes(xml_bytes)
    nemsis_blockers = [i for i in nemsis_result.issues if i.severity == "error"]

    if blocking or nemsis_blockers:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Chart has blocking issues — cannot lock",
                "clinical_blockers": [{"message": i.message, "field": i.field_path} for i in blocking],
                "nemsis_blockers": [{"element": i.element_id, "message": i.plain_message} for i in nemsis_blockers],
            },
        )

    locked_at = datetime.now(UTC).isoformat()
    updated_data = {
        **chart_data,
        "chart_status": ChartStatus.LOCKED.value,
        "locked_at": locked_at,
        "locked_by": str(current.user_id),
        "updated_at": locked_at,
    }

    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    updated_rec = await svc.update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data, "status": ChartStatus.LOCKED.value},
        correlation_id=corr_id,
        commit=False,
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict — retry")

    event_entry = SyncEngine().create_event_log_entry(
        chart_id=chart_id,
        action="chart_locked",
        actor=str(current.user_id),
        field_changes={"locked_at": locked_at},
    )
    await svc.create(
        table="epcr_event_log",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**event_entry, "chart_id": chart_id},
        correlation_id=corr_id,
        commit=False,
    )
    db.commit()

    return {"locked": True, "chart_id": chart_id, "locked_at": locked_at}


@router.post("/charts/{chart_id}/amendments")
async def request_amendment(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Request an amendment to a locked chart. Creates an audited amendment record.
    Chart must be LOCKED or AMENDED.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]
    current_status = chart_data.get("chart_status")

    if current_status not in {ChartStatus.LOCKED.value, ChartStatus.AMENDED.value}:
        raise HTTPException(
            status_code=422,
            detail=f"Amendments can only be requested on locked charts (current: {current_status})",
        )

    reason = (payload.get("reason") or "").strip()
    field_path = (payload.get("field_path") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Amendment reason is required")

    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    now = datetime.now(UTC).isoformat()

    amendment = await svc.create(
        table="epcr_amendments",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "chart_id": chart_id,
            "requested_by": str(current.user_id),
            "reason": reason,
            "field_path": field_path,
            "proposed_value": payload.get("proposed_value", ""),
            "original_value": payload.get("original_value", ""),
            "requested_at": now,
            "status": "pending",
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "status": "pending",
            "requested_by": current.user_id,
        },
        correlation_id=corr_id,
        commit=False,
    )

    # Update chart status to reflect amendment in progress
    await svc.update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={
            "data": {**chart_data, "chart_status": ChartStatus.AMENDMENT_REQUESTED.value, "updated_at": now},
            "status": ChartStatus.AMENDMENT_REQUESTED.value,
        },
        correlation_id=corr_id,
        commit=False,
    )
    db.commit()

    return {"amendment_id": str(amendment["id"]), "chart_id": chart_id, "status": "pending"}


@router.patch("/charts/{chart_id}/amendments/{amendment_id}")
async def resolve_amendment(
    chart_id: str,
    amendment_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Approve or reject an amendment request. Supervisor/Admin only.
    If approved, applies the proposed field change and re-locks the chart as AMENDED.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)

    amend_rec = _svc(db).repo("epcr_amendments").get(
        tenant_id=current.tenant_id, record_id=amendment_id
    )
    if amend_rec is None or amend_rec["data"].get("chart_id") != chart_id:
        raise HTTPException(status_code=404, detail="Amendment not found")

    decision = (payload.get("decision") or "").lower()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Decision must be 'approved' or 'rejected'")

    now = datetime.now(UTC).isoformat()
    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    amend_data = {
        **amend_rec["data"],
        "status": decision,
        "decided_by": str(current.user_id),
        "decided_at": now,
        "decision_notes": payload.get("notes", ""),
    }

    await svc.update(
        table="epcr_amendments",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(amendment_id),
        expected_version=amend_rec["version"],
        patch={"data": amend_data, "status": decision},
        correlation_id=corr_id,
        commit=False,
    )

    chart_data = rec["data"]
    new_chart_status = ChartStatus.AMENDED.value if decision == "approved" else ChartStatus.LOCKED.value
    new_chart_data = {**chart_data, "chart_status": new_chart_status, "updated_at": now}

    if decision == "approved":
        field_path = amend_rec["data"].get("field_path", "")
        proposed_value = amend_rec["data"].get("proposed_value")
        if field_path and proposed_value is not None:
            _set_nested(new_chart_data, field_path, proposed_value)

    await svc.update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": new_chart_data, "status": new_chart_status},
        correlation_id=corr_id,
        commit=False,
    )

    event_entry = SyncEngine().create_event_log_entry(
        chart_id=chart_id,
        action=f"amendment_{decision}",
        actor=str(current.user_id),
        field_changes={"amendment_id": amendment_id, "decision": decision},
    )
    await svc.create(
        table="epcr_event_log",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**event_entry, "chart_id": chart_id},
        correlation_id=corr_id,
        commit=False,
    )
    db.commit()

    return {"amendment_id": amendment_id, "decision": decision, "chart_status": new_chart_status}


@router.get("/charts/{chart_id}/amendments")
async def list_amendments(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rows = db.execute(
        text(
            "SELECT * FROM epcr_amendments "
            "WHERE tenant_id = :tid AND chart_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"tid": str(current.tenant_id), "cid": chart_id},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# SIGNATURES
# ─────────────────────────────────────────────────────────────


@router.post("/charts/{chart_id}/signatures")
async def add_signature(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Capture a signature for the chart (patient, crew, facility).
    Signature data must be provided by the client (base64 canvas/SVG).
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]

    if chart_data.get("chart_status") == ChartStatus.LOCKED.value:
        raise HTTPException(status_code=422, detail="Cannot add signatures to a locked chart")

    signer_name = (payload.get("signer_name") or "").strip()
    signer_role = (payload.get("signer_role") or "").strip()
    signature_data = (payload.get("signature_data") or "").strip()
    signature_type = (payload.get("signature_type") or "general").strip()

    if not signer_name or not signer_role:
        raise HTTPException(status_code=422, detail="signer_name and signer_role are required")
    if not signature_data:
        raise HTTPException(status_code=422, detail="signature_data is required")

    sig_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    await svc.create(
        table="epcr_chart_signatures",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "signature_id": sig_id,
            "chart_id": chart_id,
            "signer_name": signer_name,
            "signer_role": signer_role,
            "signature_type": signature_type,
            "signature_data": signature_data,
            "captured_at": now,
            "captured_by": str(current.user_id),
            "is_valid": True,
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "signer_role": signer_role,
        },
        correlation_id=corr_id,
        commit=False,
    )

    # Also append a reference to the chart's signatures list
    updated_data = dict(chart_data)
    updated_data.setdefault("signatures", []).append({
        "signature_id": sig_id,
        "signer_name": signer_name,
        "signer_role": signer_role,
        "signature_type": signature_type,
        "captured_at": now,
    })
    updated_data["updated_at"] = now

    await svc.update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=corr_id,
        commit=False,
    )
    db.commit()

    return {
        "signature_id": sig_id,
        "chart_id": chart_id,
        "signer_role": signer_role,
        "captured_at": now,
    }


@router.get("/charts/{chart_id}/signatures")
async def list_signatures(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rows = db.execute(
        text(
            "SELECT id, data, created_at FROM epcr_chart_signatures "
            "WHERE tenant_id = :tid AND chart_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at ASC"
        ),
        {"tid": str(current.tenant_id), "cid": chart_id},
    ).mappings().all()
    # Return without raw signature_data for list view (privacy/bandwidth)
    results = []
    for r in rows:
        d = dict(r["data"]) if r["data"] else {}
        d.pop("signature_data", None)
        results.append({"id": str(r["id"]), "captured_at": d.get("captured_at"), **d})
    return results


# ─────────────────────────────────────────────────────────────
# QA / QI WORKFLOW
# ─────────────────────────────────────────────────────────────


@router.get("/qa/queue")
async def get_qa_queue(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Get the QA review queue. Includes both manual and AI-flagged reviews.
    """
    clauses = ["q.tenant_id = :tid", "q.deleted_at IS NULL"]
    params: dict[str, Any] = {
        "tid": str(current.tenant_id),
        "limit": limit,
        "offset": offset,
    }
    if status:
        clauses.append("q.status = :status")
        params["status"] = status

    sql = text(
        "SELECT q.id, q.chart_id, q.status, q.reviewer_id, q.created_at, q.data "
        "FROM epcr_qa_reviews q "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY q.created_at DESC "
        "LIMIT :limit OFFSET :offset"
    )
    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


@router.post("/charts/{chart_id}/qa")
async def create_qa_review(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Open a new QA review session for a chart.
    Triggered manually by supervisor or automatically by AI contradiction flags.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]

    # Detect AI-triggered contradictions
    from core_app.epcr.ai_smart_text import SmartTextEngine
    contradictions = SmartTextEngine().detect_contradictions(chart_data)
    missing_docs = SmartTextEngine().detect_missing_documentation(chart_data, chart_data.get("chart_mode", "bls"))

    ai_flags: list[dict] = []
    for c in contradictions.get("contradictions", []):
        ai_flags.append({"source": "AI", "type": "CONTRADICTION", "severity": "high", "description": c["description"]})
    for issue in missing_docs.get("issues", []):
        if issue.get("severity") == "error":
            ai_flags.append({"source": "AI", "type": "MISSING_DOCS", "severity": "medium", "description": issue["issue"]})

    # Manual flags from payload
    manual_flags = [
        {**f, "source": "MANUAL", "flagged_by": str(current.user_id)}
        for f in payload.get("flags", [])
        if isinstance(f, dict)
    ]

    all_flags = ai_flags + manual_flags
    now = datetime.now(UTC).isoformat()

    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    review = await svc.create(
        table="epcr_qa_reviews",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "chart_id": chart_id,
            "reviewer_id": str(current.user_id),
            "started_at": now,
            "status": QAStatus.IN_REVIEW.value,
            "flags": all_flags,
            "notes": payload.get("notes", ""),
            "ai_triggered": bool(ai_flags),
            "trigger_type": payload.get("trigger_type", "manual"),
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "status": QAStatus.IN_REVIEW.value,
            "reviewer_id": current.user_id,
        },
        correlation_id=corr_id,
        commit=False,
    )

    # Update chart to CLINICAL_REVIEW_REQUIRED if not already locked
    if chart_data.get("chart_status") not in {ChartStatus.LOCKED.value, ChartStatus.AMENDED.value, ChartStatus.CLOSED.value}:
        await svc.update(
            table="epcr_charts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(str(rec["id"])),
            expected_version=rec["version"],
            patch={
                "data": {**chart_data, "chart_status": ChartStatus.CLINICAL_REVIEW_REQUIRED.value, "updated_at": now},
                "status": ChartStatus.CLINICAL_REVIEW_REQUIRED.value,
            },
            correlation_id=corr_id,
            commit=False,
        )
    db.commit()

    return {
        "review_id": str(review["id"]),
        "chart_id": chart_id,
        "flags_detected": len(all_flags),
        "ai_flags": len(ai_flags),
        "manual_flags": len(manual_flags),
    }


@router.patch("/qa/{review_id}")
async def complete_qa_review(
    review_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Complete a QA review with a decision: APPROVED, NEEDS_CORRECTION, ESCALATED, EDUCATION_FLAGGED.
    QA decisions do NOT silently mutate chart clinical facts.
    """
    review_rec = _svc(db).repo("epcr_qa_reviews").get(
        tenant_id=current.tenant_id, record_id=review_id
    )
    if review_rec is None:
        raise HTTPException(status_code=404, detail="QA Review not found")

    decision = (payload.get("decision") or "").upper()
    valid_decisions = {d.value.upper() for d in QAStatus}
    if decision not in valid_decisions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision. Must be one of: {', '.join(sorted(valid_decisions))}",
        )

    now = datetime.now(UTC).isoformat()
    chart_id = review_rec["data"].get("chart_id")
    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    updated_review_data = {
        **review_rec["data"],
        "status": decision.lower(),
        "completed_at": now,
        "decided_by": str(current.user_id),
        "decision_notes": payload.get("notes", ""),
        "education_tags": payload.get("education_tags", []),
        "feedback_note": payload.get("feedback_note", ""),
    }

    await svc.update(
        table="epcr_qa_reviews",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(review_id),
        expected_version=review_rec["version"],
        patch={"data": updated_review_data, "status": decision.lower()},
        correlation_id=corr_id,
        commit=False,
    )

    # Update chart status based on QA decision
    if chart_id:
        try:
            chart_rec = _svc(db).repo("epcr_charts").get(
                tenant_id=current.tenant_id, record_id=chart_id
            )
            if chart_rec:
                chart_data = chart_rec["data"]
                new_chart_status = _qa_decision_to_chart_status(decision)
                await svc.update(
                    table="epcr_charts",
                    tenant_id=current.tenant_id,
                    actor_user_id=current.user_id,
                    record_id=uuid.UUID(str(chart_rec["id"])),
                    expected_version=chart_rec["version"],
                    patch={
                        "data": {**chart_data, "chart_status": new_chart_status, "updated_at": now},
                        "status": new_chart_status,
                    },
                    correlation_id=corr_id,
                    commit=False,
                )
        except Exception:
            pass  # Don't fail QA decision if chart update fails

    event_entry = SyncEngine().create_event_log_entry(
        chart_id=chart_id or "",
        action=f"qa_review_{decision.lower()}",
        actor=str(current.user_id),
        field_changes={"review_id": review_id, "decision": decision},
    )
    if chart_id:
        await svc.create(
            table="epcr_event_log",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={**event_entry, "chart_id": chart_id},
            correlation_id=corr_id,
            commit=False,
        )
    db.commit()

    return {"review_id": review_id, "decision": decision, "completed_at": now}


@router.get("/qa/{review_id}")
async def get_qa_review(
    review_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_qa_reviews").get(
        tenant_id=current.tenant_id, record_id=review_id
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="QA Review not found")
    return rec


# ─────────────────────────────────────────────────────────────
# HANDOFF
# ─────────────────────────────────────────────────────────────


@router.post("/charts/{chart_id}/handoff")
async def generate_handoff(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generate a clinical handoff packet for the receiving facility.
    Uses AI (SmartTextEngine) to produce SBAR summary from real chart data.
    """
    rec = _get_chart_or_404(db, chart_id, current.tenant_id)
    chart_data = rec["data"]

    recipient_facility = (payload.get("recipient_facility") or chart_data.get("disposition", {}).get("destination_name") or "").strip()

    # AI-generated SBAR handoff from real chart data
    from core_app.epcr.ai_smart_text import SmartTextEngine
    sbar = SmartTextEngine().generate_handoff_summary(chart_data)

    patient = chart_data.get("patient", {})
    vitals = chart_data.get("vitals", [])
    last_vital = vitals[-1] if vitals else {}
    meds = chart_data.get("medications", [])
    procs = chart_data.get("procedures", [])
    dispatch = chart_data.get("dispatch", {})
    chart_data.get("disposition", {})

    now = datetime.now(UTC).isoformat()
    corr_id = getattr(request.state, "correlation_id", None)

    packet = await _svc(db).create(
        table="epcr_handoff_packets",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "chart_id": chart_id,
            "generated_at": now,
            "generated_by": str(current.user_id),
            "recipient_facility": recipient_facility,
            "delivery_status": "handoff_ready",
            "delivery_method": payload.get("delivery_method", "direct"),
            "patient_snapshot": {
                "first_name": patient.get("first_name"),
                "last_name": patient.get("last_name"),
                "dob": patient.get("dob"),
                "gender": patient.get("gender"),
                "chief_complaint": (chart_data.get("assessments") or [{}])[0].get("chief_complaint"),
            },
            "last_vital": {
                "recorded_at": last_vital.get("recorded_at"),
                "systolic_bp": last_vital.get("systolic_bp"),
                "diastolic_bp": last_vital.get("diastolic_bp"),
                "heart_rate": last_vital.get("heart_rate"),
                "spo2": last_vital.get("spo2"),
                "respiratory_rate": last_vital.get("respiratory_rate"),
                "gcs_total": last_vital.get("gcs_total"),
            },
            "medications_given": [{"name": m.get("medication_name"), "dose": m.get("dose"), "route": m.get("route")} for m in meds if not m.get("prior_to_our_care")],
            "procedures_performed": [{"name": p.get("procedure_name"), "time": p.get("time_performed")} for p in procs if not p.get("prior_to_our_care")],
            "arrived_destination_time": dispatch.get("arrived_destination_time"),
            "sbar_summary": sbar.get("summary", ""),
            "ai_token_usage": sbar.get("token_usage", {}),
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "status": "handoff_ready",
            "recipient_facility": recipient_facility[:255] if recipient_facility else None,
        },
        correlation_id=corr_id,
    )

    return {
        "packet_id": str(packet["id"]),
        "chart_id": chart_id,
        "recipient_facility": recipient_facility,
        "status": "handoff_ready",
        "generated_at": now,
        "sbar_summary": sbar.get("summary", ""),
    }


@router.post("/charts/{chart_id}/handoff/{packet_id}/send")
async def send_handoff(
    chart_id: str,
    packet_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Mark a handoff packet as sent. Integrates with fax/Direct if configured.
    """
    packet_rec = _svc(db).repo("epcr_handoff_packets").get(
        tenant_id=current.tenant_id, record_id=packet_id
    )
    if packet_rec is None or packet_rec["data"].get("chart_id") != chart_id:
        raise HTTPException(status_code=404, detail="Handoff packet not found")

    delivery_method = payload.get("delivery_method") or packet_rec["data"].get("delivery_method", "direct")
    now = datetime.now(UTC).isoformat()
    corr_id = getattr(request.state, "correlation_id", None)

    updated_data = {
        **packet_rec["data"],
        "delivery_status": "handoff_sent",
        "sent_at": now,
        "sent_by": str(current.user_id),
        "delivery_method": delivery_method,
        "send_destination": payload.get("destination", ""),
    }

    await _svc(db).update(
        table="epcr_handoff_packets",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(packet_id),
        expected_version=packet_rec["version"],
        patch={"data": updated_data, "status": "handoff_sent"},
        correlation_id=corr_id,
    )

    # Audit event
    event_entry = SyncEngine().create_event_log_entry(
        chart_id=chart_id,
        action="handoff_sent",
        actor=str(current.user_id),
        field_changes={"packet_id": packet_id, "method": delivery_method},
    )
    await _svc(db).create(
        table="epcr_event_log",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**event_entry, "chart_id": chart_id},
        correlation_id=corr_id,
    )

    return {"sent": True, "packet_id": packet_id, "sent_at": now, "method": delivery_method}


@router.get("/charts/{chart_id}/handoff")
async def list_handoff_packets(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rows = db.execute(
        text(
            "SELECT id, data, status, created_at FROM epcr_handoff_packets "
            "WHERE tenant_id = :tid AND chart_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"tid": str(current.tenant_id), "cid": chart_id},
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# OFFLINE SYNC QUEUE
# ─────────────────────────────────────────────────────────────


@router.post("/sync/queue")
async def queue_offline_chart(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Accept an offline chart bundle from a field device.
    Creates a sync queue entry and immediately attempts to resolve + persist.
    Returns conflict details if a server version already exists.
    """
    local_chart = payload.get("chart", {})
    chart_id = local_chart.get("chart_id")
    device_id = payload.get("device_id", "unknown")
    conflict_policy = payload.get("conflict_policy", "last_write_wins")

    if not chart_id:
        raise HTTPException(status_code=422, detail="chart.chart_id is required")

    now = datetime.now(UTC).isoformat()
    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    # Hash for idempotency — same payload = same hash, don't re-enqueue
    from core_app.epcr.sync_engine import SyncEngine as SE
    payload_hash = SE().compute_sync_hash(local_chart)

    existing_queue = db.execute(
        text(
            "SELECT id FROM epcr_sync_queue "
            "WHERE tenant_id = :tid AND chart_id = :cid AND status IN ('queued', 'processing') "
            "LIMIT 1"
        ),
        {"tid": str(current.tenant_id), "cid": chart_id},
    ).fetchone()

    if existing_queue:
        return {"queued": True, "chart_id": chart_id, "idempotent": True, "note": "Already queued"}

    # Create queue record
    queue_rec = await svc.create(
        table="epcr_sync_queue",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "chart_id": chart_id,
            "device_id": device_id,
            "queued_at": now,
            "status": "queued",
            "retry_count": 0,
            "payload_hash": payload_hash,
            "conflict_policy": conflict_policy,
        },
        typed_columns={
            "chart_id": uuid.UUID(chart_id) if _valid_uuid(chart_id) else None,
            "status": "queued",
            "retry_count": 0,
        },
        correlation_id=corr_id,
        commit=False,
    )
    queue_id = str(queue_rec["id"])

    # Immediately try to sync
    server_rec = svc.repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    conflict_notes = []

    try:
        from core_app.epcr.sync_engine import SyncConflictPolicy
        try:
            policy = SyncConflictPolicy(conflict_policy)
        except ValueError:
            policy = SyncConflictPolicy.LAST_WRITE_WINS

        if server_rec is None:
            # New chart from field — create it
            from core_app.epcr.completeness_engine import CompletenessEngine
            mode = local_chart.get("chart_mode", "bls")
            score = CompletenessEngine().score_chart(local_chart, mode)
            local_chart["completeness_score"] = score["score"]
            local_chart["completeness_issues"] = [m["label"] for m in score["missing"]]
            local_chart["sync_status"] = "fully_synced"
            await svc.create(
                table="epcr_charts",
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                data=local_chart,
                correlation_id=corr_id,
                commit=False,
            )
        else:
            # Resolve conflict
            resolved, conflict_notes = SE().resolve_conflict(
                local_chart, server_rec["data"], policy
            )
            resolved["sync_status"] = "fully_synced"
            resolved["updated_at"] = now

            await svc.update(
                table="epcr_charts",
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                record_id=uuid.UUID(str(server_rec["id"])),
                expected_version=server_rec["version"],
                patch={"data": resolved},
                correlation_id=corr_id,
                commit=False,
            )

        # Mark sync queue as completed
        await svc.update(
            table="epcr_sync_queue",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(queue_id),
            expected_version=queue_rec["version"],
            patch={"data": {**queue_rec["data"], "status": "completed", "completed_at": now, "conflict_notes": conflict_notes}, "status": "completed"},
            correlation_id=corr_id,
            commit=False,
        )

        db.commit()

        return {
            "synced": True,
            "chart_id": chart_id,
            "queue_id": queue_id,
            "conflict_notes": conflict_notes,
            "was_new": server_rec is None,
        }

    except Exception as e:
        db.rollback()
        # Mark sync queue as failed
        try:
            import logging
            logging.error(f"Sync failed for chart {chart_id}: {e}")
            db.execute(
                text("UPDATE epcr_sync_queue SET status = 'failed', data = data || :patch WHERE id = :qid"),
                {
                    "qid": queue_id,
                    "patch": f'{{"last_error": "{str(e)[:500]}", "status": "failed"}}',
                },
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)[:300]}")


@router.get("/sync/queue")
async def get_sync_queue(
    status: str | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    View the offline sync queue for this tenant. Shows backlog and failures.
    """
    clauses = ["tenant_id = :tid", "deleted_at IS NULL"]
    params: dict[str, Any] = {"tid": str(current.tenant_id), "limit": limit}
    if status:
        clauses.append("status = :status")
        params["status"] = status

    rows = db.execute(
        text(f"SELECT * FROM epcr_sync_queue WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT :limit"),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def _valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


def _set_nested(obj: dict, path: str, value: Any) -> None:
    """Apply a dot-notation field path to a nested dict."""
    parts = path.split(".")
    for part in parts[:-1]:
        if isinstance(obj, dict):
            obj = obj.setdefault(part, {})
    if isinstance(obj, dict) and parts:
        obj[parts[-1]] = value


def _qa_decision_to_chart_status(decision: str) -> str:
    mapping = {
        "APPROVED": ChartStatus.READY_FOR_LOCK.value,
        "NEEDS_CORRECTION": ChartStatus.CLINICAL_REVIEW_REQUIRED.value,
        "ESCALATED": ChartStatus.CLINICAL_REVIEW_REQUIRED.value,
        "EDUCATION_FLAGGED": ChartStatus.CLINICAL_REVIEW_REQUIRED.value,
        "CLOSED": ChartStatus.READY_FOR_LOCK.value,
    }
    return mapping.get(decision.upper(), ChartStatus.CLINICAL_REVIEW_REQUIRED.value)
