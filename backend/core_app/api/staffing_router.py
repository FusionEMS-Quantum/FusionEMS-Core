"""
Staffing Router — FusionEMS-Core
Crew qualification, availability, conflict detection,
fatigue flags, and staffing readiness summary.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.staffing.readiness_engine import StaffingReadinessEngine

router = APIRouter(prefix="/api/v1/staffing", tags=["Staffing"])


def _engine(db: Session, current: CurrentUser) -> StaffingReadinessEngine:
    return StaffingReadinessEngine(db, get_event_publisher(), current.tenant_id, current.user_id)


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


# ── Readiness Summary ─────────────────────────────────────────────────────────

@router.get("/readiness")
async def staffing_readiness(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Agency-wide staffing readiness snapshot."""
    engine = _engine(db, current)
    return engine.staffing_readiness_summary()


# ── Qualification Check ───────────────────────────────────────────────────────

@router.get("/crew/{crew_member_id}/qualification")
async def check_qualification(
    crew_member_id: str,
    service_level: str = "BLS",
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Deterministic qualification check for a crew member.
    Cannot be silently overridden.
    """
    engine = _engine(db, current)
    return engine.check_crew_qualification(crew_member_id, service_level)


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/crew/{crew_member_id}/availability")
async def check_availability(
    crew_member_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Check crew availability and active conflicts."""
    engine = _engine(db, current)
    return engine.check_crew_availability(crew_member_id)


@router.post("/crew/{crew_member_id}/availability")
async def set_availability(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Set crew member availability status."""
    status = payload.get("status")
    if not status:
        return {"error": "status_required"}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    record = await svc.create(
        table="crew_availability",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "crew_member_id": crew_member_id,
            "status": status,
            "set_by": str(current.user_id),
            "note": payload.get("note"),
            **{k: v for k, v in payload.items() if k not in ("status", "note")},
        },
        correlation_id=corr,
    )
    return record


# ── Conflict Detection ────────────────────────────────────────────────────────

@router.post("/crew/{crew_member_id}/conflict-check")
async def conflict_check(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Detect assignment conflicts before finalizing a crew assignment."""
    mission_id = payload.get("proposed_mission_id")
    unit_id = payload.get("proposed_unit_id")
    if not mission_id or not unit_id:
        return {"error": "proposed_mission_id and proposed_unit_id required"}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.detect_assignment_conflict(
        crew_member_id=crew_member_id,
        proposed_mission_id=mission_id,
        proposed_unit_id=unit_id,
        correlation_id=corr,
    )


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Resolve an assignment conflict with a required reason."""
    reason = payload.get("reason")
    if not reason:
        return {"error": "resolve_reason_required"}

    svc = _svc(db)
    conflict = svc.repo("crew_assignment_conflicts").get(
        tenant_id=current.tenant_id, record_id=conflict_id
    )
    if not conflict:
        return {"error": "not_found"}

    updated = svc.repo("crew_assignment_conflicts").update(
        tenant_id=current.tenant_id,
        record_id=conflict_id,
        expected_version=(conflict.get("version") or 1),
        patch={
            "resolved": True,
            "resolved_by": str(current.user_id),
            "resolve_reason": reason,
        },
    )
    return updated or {"error": "update_failed"}


# ── Qualifications CRUD ───────────────────────────────────────────────────────

@router.post("/crew/{crew_member_id}/qualifications")
async def add_qualification(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Add a certification/qualification record for a crew member."""
    required = ["certification_type", "issued_at", "expires_at"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "fields": missing}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="crew_qualifications",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "crew_member_id": crew_member_id,
            "status": "ACTIVE",
            **payload,
        },
        correlation_id=corr,
    )


@router.get("/crew/{crew_member_id}/qualifications")
async def list_qualifications(
    crew_member_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """List all qualifications for a crew member."""
    svc = _svc(db)
    all_quals = svc.repo("crew_qualifications").list(
        tenant_id=current.tenant_id, limit=200
    )
    crew_quals = [q for q in all_quals if (q.get("data") or {}).get("crew_member_id") == crew_member_id]
    return {"crew_member_id": crew_member_id, "qualifications": crew_quals}


# ── Fatigue Flags ─────────────────────────────────────────────────────────────

@router.post("/crew/{crew_member_id}/fatigue-flag")
async def set_fatigue_flag(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Flag a crew member for fatigue. Cannot be silently cleared."""
    reason = payload.get("reason")
    if not reason:
        return {"error": "reason_required"}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.flag_fatigue(
        crew_member_id=crew_member_id,
        reason=reason,
        hours_on_duty=payload.get("hours_on_duty"),
        flagged_by=payload.get("flagged_by", str(current.user_id)),
        correlation_id=corr,
    )


@router.post("/crew/{crew_member_id}/fatigue-flag/clear")
async def clear_fatigue_flag(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Clear a fatigue flag with required reason. Creates audit record."""
    reason = payload.get("reason")
    flag_id = payload.get("flag_id")
    if not reason:
        return {"error": "clear_reason_required"}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    if flag_id:
        flag = svc.repo("crew_fatigue_flags").get(
            tenant_id=current.tenant_id, record_id=uuid.UUID(flag_id)
        )
        if flag:
            updated = svc.repo("crew_fatigue_flags").update(
                tenant_id=current.tenant_id,
                record_id=uuid.UUID(flag_id),
                expected_version=(flag.get("version") or 1),
                patch={
                    "cleared": True,
                    "cleared_by": str(current.user_id),
                    "clear_reason": reason,
                },
            )
            return updated or {"error": "update_failed"}

    # Audit the clear action regardless
    await svc.create(
        table="staffing_audit_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "event_type": "FATIGUE_FLAG_CLEARED",
            "crew_member_id": crew_member_id,
            "cleared_by": str(current.user_id),
            "reason": reason,
        },
        correlation_id=corr,
    )
    return {"status": "cleared", "crew_member_id": crew_member_id}


# ── Readiness Score ───────────────────────────────────────────────────────────

@router.post("/crew/{crew_member_id}/readiness-score")
async def save_crew_readiness_score(
    crew_member_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Save a crew readiness score (from external assessment)."""
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="crew_readiness_scores",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"crew_member_id": crew_member_id, **payload},
        correlation_id=corr,
    )


# ── Staffing Audit ────────────────────────────────────────────────────────────

@router.get("/audit")
async def staffing_audit(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 100,
):
    """Return staffing audit events."""
    svc = _svc(db)
    return svc.repo("staffing_audit_events").list(
        tenant_id=current.tenant_id, limit=limit
    )
