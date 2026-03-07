"""
CAD Dispatch Router — FusionEMS-Core
Full CAD/Dispatch API with state machine, mission management,
unit/crew recommendations, assignment, override, and audit.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.cad.dispatch_engine import DispatchEngine
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/dispatch", tags=["Dispatch"])

_ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher"}


def _engine(db: Session, current: CurrentUser) -> DispatchEngine:
    return DispatchEngine(db, get_event_publisher(), current.tenant_id, current.user_id)


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


# ── Dispatch Requests ─────────────────────────────────────────────────────────

@router.post("/requests")
async def create_dispatch_request(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Create a new dispatch request (pre-mission intake).
    Validates required fields before CAD injection.
    """
    required = ["service_level", "priority", "origin_address"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "fields": missing}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    record = await svc.create(
        table="dispatch_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **payload,
            "state": "REQUEST_CREATED",
            "submitted_by": str(current.user_id),
        },
        correlation_id=corr,
    )
    return record


@router.post("/requests/{request_id}/validate")
async def validate_dispatch_request(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Validate a dispatch request and mark it ready for CAD injection."""
    svc = _svc(db)
    rec = svc.repo("dispatch_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    if not rec:
        return {"error": "not_found"}

    updated = svc.repo("dispatch_requests").update(
        tenant_id=current.tenant_id,
        record_id=request_id,
        expected_version=(rec.get("version") or 1),
        patch={"state": "REQUEST_VALIDATED", "validated_by": str(current.user_id)},
    )
    return updated or {"error": "update_failed"}


@router.post("/requests/{request_id}/inject")
async def inject_to_cad(
    request_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Inject a validated dispatch request into CAD as an active mission.
    Creates full mission record with initial NEW_REQUEST state.
    """
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    req_rec = svc.repo("dispatch_requests").get(
        tenant_id=current.tenant_id, record_id=request_id
    )
    if not req_rec:
        return {"error": "dispatch_request_not_found"}

    req_data = req_rec.get("data") or {}
    state = req_data.get("state")
    if state == "REQUEST_REJECTED":
        return {"error": "cannot_inject_rejected_request"}

    engine = _engine(db, current)
    mission = await engine.create_mission(
        dispatch_request_id=request_id,
        service_level=req_data.get("service_level", "BLS"),
        priority=req_data.get("priority", "P2"),
        chief_complaint=req_data.get("chief_complaint", ""),
        origin_address=req_data.get("origin_address", ""),
        destination_address=req_data.get("destination_address"),
        agency_id=req_data.get("agency_id"),
        correlation_id=corr,
        metadata=payload.get("metadata"),
    )

    # Update request state
    svc.repo("dispatch_requests").update(
        tenant_id=current.tenant_id,
        record_id=request_id,
        expected_version=(req_rec.get("version") or 1),
        patch={"state": "DISPATCH_INJECTED", "mission_id": str(mission["id"])},
    )

    return {"mission": mission, "dispatch_request_id": str(request_id)}


# ── Active Missions ───────────────────────────────────────────────────────────

@router.get("/missions")
async def list_missions(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 100,
    offset: int = 0,
    state: str | None = None,
):
    """List active missions, optionally filtered by state."""
    svc = _svc(db)
    missions = svc.repo("active_missions").list(
        tenant_id=current.tenant_id, limit=limit, offset=offset
    )
    if state:
        missions = [m for m in missions if (m.get("data") or {}).get("state") == state]
    return {"missions": missions, "count": len(missions)}


@router.get("/missions/{mission_id}")
async def get_mission(
    mission_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Get a single mission with full timeline."""
    svc = _svc(db)
    mission = svc.repo("active_missions").get(
        tenant_id=current.tenant_id, record_id=mission_id
    )
    if not mission:
        return {"error": "not_found"}

    timeline = [
        e for e in svc.repo("dispatch_timeline_events").list(
            tenant_id=current.tenant_id, limit=100
        )
        if (e.get("data") or {}).get("mission_id") == str(mission_id)
    ]
    audit = [
        e for e in svc.repo("mission_audit_events").list(
            tenant_id=current.tenant_id, limit=100
        )
        if (e.get("data") or {}).get("mission_id") == str(mission_id)
    ]

    return {"mission": mission, "timeline": timeline, "audit_trail": audit}


@router.post("/missions/{mission_id}/transition")
async def transition_mission(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Transition a mission to a new dispatch state.
    Override requires explicit reason — creates audit record.
    """
    target_state = payload.get("state")
    if not target_state:
        return {"error": "state_required"}

    override = bool(payload.get("override"))
    override_reason = payload.get("override_reason")
    corr = getattr(request.state, "correlation_id", None)

    engine = _engine(db, current)
    return await engine.transition_mission(
        mission_id=mission_id,
        target_state=target_state,
        actor_user_id=current.user_id,
        override=override,
        override_reason=override_reason,
        metadata=payload.get("metadata"),
        correlation_id=corr,
    )


# ── Recommendations ───────────────────────────────────────────────────────────

@router.post("/missions/{mission_id}/recommend/unit")
async def recommend_unit(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Recommend available units for this mission based on service level."""
    svc = _svc(db)
    mission = svc.repo("active_missions").get(
        tenant_id=current.tenant_id, record_id=mission_id
    )
    if not mission:
        return {"error": "not_found"}

    mdata = mission.get("data") or {}
    engine = _engine(db, current)
    rec = engine.recommend_unit(
        service_level=payload.get("service_level") or mdata.get("service_level", "BLS"),
        origin_lat=payload.get("origin_lat"),
        origin_lon=payload.get("origin_lon"),
        priority=payload.get("priority") or mdata.get("priority", "P2"),
    )

    # Save recommendation
    svc_obj = _svc(db)
    await svc_obj.create(
        table="dispatch_recommendations",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "type": "UNIT",
            "recommendation": rec,
        },
        correlation_id=None,
    )
    return rec


@router.post("/missions/{mission_id}/recommend/crew")
async def recommend_crew(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Recommend qualified crew for a mission and unit."""
    svc = _svc(db)
    mission = svc.repo("active_missions").get(
        tenant_id=current.tenant_id, record_id=mission_id
    )
    if not mission:
        return {"error": "not_found"}

    mdata = mission.get("data") or {}
    unit_id_str = payload.get("unit_id") or mdata.get("assigned_unit_id")
    if not unit_id_str:
        return {"error": "unit_id_required"}

    engine = _engine(db, current)
    rec = engine.recommend_crew(
        unit_id=uuid.UUID(unit_id_str),
        service_level=payload.get("service_level") or mdata.get("service_level", "BLS"),
    )
    return rec


# ── Assignment ────────────────────────────────────────────────────────────────

@router.post("/missions/{mission_id}/assign")
async def assign_mission(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Assign a unit and crew to a mission.
    Override is allowed with explicit reason — creates full audit record.
    """
    unit_id_str = payload.get("unit_id")
    crew_ids = payload.get("crew_member_ids") or []
    override = bool(payload.get("override"))
    override_reason = payload.get("override_reason")
    corr = getattr(request.state, "correlation_id", None)

    if not unit_id_str:
        return {"error": "unit_id_required"}
    if not crew_ids:
        return {"error": "crew_member_ids_required"}

    engine = _engine(db, current)
    return await engine.assign_unit_and_crew(
        mission_id=mission_id,
        unit_id=uuid.UUID(unit_id_str),
        crew_member_ids=crew_ids,
        assigned_by=payload.get("assigned_by", "DISPATCHER"),
        override=override,
        override_reason=override_reason,
        correlation_id=corr,
    )


# ── Ops Board ─────────────────────────────────────────────────────────────────

@router.get("/ops/board")
async def ops_board(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Real-time ops board for founder command center.
    Returns active missions, unassigned, escalated pages, and late pages.
    """
    engine = _engine(db, current)
    return engine.get_ops_board()


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/missions/{mission_id}/cancel")
async def cancel_mission(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Cancel a mission with required reason."""
    reason = payload.get("reason")
    if not reason:
        return {"error": "cancel_reason_required"}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.transition_mission(
        mission_id=mission_id,
        target_state="CANCELLED",
        actor_user_id=current.user_id,
        override=True,
        override_reason=reason,
        metadata={"cancelled_by": str(current.user_id), "reason": reason},
        correlation_id=corr,
    )


# ── Audit Trail ───────────────────────────────────────────────────────────────

@router.get("/missions/{mission_id}/audit")
async def mission_audit(
    mission_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Return full audit trail for a mission."""
    svc = _svc(db)
    audit = [
        e for e in svc.repo("mission_audit_events").list(
            tenant_id=current.tenant_id, limit=200
        )
        if (e.get("data") or {}).get("mission_id") == str(mission_id)
    ]
    timeline = [
        e for e in svc.repo("dispatch_timeline_events").list(
            tenant_id=current.tenant_id, limit=200
        )
        if (e.get("data") or {}).get("mission_id") == str(mission_id)
    ]
    return {
        "mission_id": str(mission_id),
        "audit_events": audit,
        "timeline_events": timeline,
    }
