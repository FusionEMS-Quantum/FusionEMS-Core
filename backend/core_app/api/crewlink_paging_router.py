"""
CrewLink Paging Router — FusionEMS-Core
Full paging API: alert creation, push delivery, crew response,
escalation, backup paging, and audit.

HARD BOUNDARY: No billing content. No Telnyx. Operations only.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.crewlink.paging_engine import CrewLinkPagingEngine, CrewResponse
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/crewlink", tags=["CrewLink"])


def _engine(db: Session, current: CurrentUser) -> CrewLinkPagingEngine:
    return CrewLinkPagingEngine(db, get_event_publisher(), current.tenant_id, current.user_id)


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


# ── Alert Creation ────────────────────────────────────────────────────────────

@router.post("/alerts")
async def create_alert(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Create a new CrewLink paging alert for a mission.
    Resolves targets, creates recipients, queues push notifications.
    OPERATIONS ONLY — no billing content permitted.
    """
    required = ["mission_id", "mission_title", "mission_address", "target_crew_ids"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "fields": missing}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.create_paging_alert(
        mission_id=payload["mission_id"],
        mission_title=payload["mission_title"],
        mission_address=payload["mission_address"],
        service_level=payload.get("service_level", "BLS"),
        priority=payload.get("priority", "P2"),
        target_crew_ids=payload["target_crew_ids"],
        unit_id=payload.get("unit_id"),
        chief_complaint=payload.get("chief_complaint"),
        special_instructions=payload.get("special_instructions"),
        ack_timeout_seconds=int(payload.get("ack_timeout_seconds", 120)),
        accept_timeout_seconds=int(payload.get("accept_timeout_seconds", 300)),
        escalation_rules=payload.get("escalation_rules"),
        correlation_id=corr,
    )


@router.get("/alerts")
async def list_alerts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 100,
    state: str | None = None,
):
    """List CrewLink paging alerts."""
    svc = _svc(db)
    alerts = svc.repo("crew_paging_alerts").list(
        tenant_id=current.tenant_id, limit=limit
    )
    if state:
        alerts = [a for a in alerts if (a.get("data") or {}).get("state") == state]
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/alerts/active")
async def active_alerts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Get all active (non-closed) paging alerts."""
    svc = _svc(db)
    alerts = svc.repo("crew_paging_alerts").list(
        tenant_id=current.tenant_id, limit=200
    )
    terminal = {"CLOSED", "ACCEPTED"}
    active = [a for a in alerts if (a.get("data") or {}).get("state") not in terminal]
    return {"alerts": active, "count": len(active)}


@router.get("/alerts/{alert_id}")
async def get_alert(
    alert_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Get a paging alert with recipients, responses, and audit trail."""
    svc = _svc(db)
    alert = svc.repo("crew_paging_alerts").get(
        tenant_id=current.tenant_id, record_id=alert_id
    )
    if not alert:
        return {"error": "not_found"}

    aid = str(alert_id)
    recipients = [
        r for r in svc.repo("crew_paging_recipients").list(
            tenant_id=current.tenant_id, limit=50
        )
        if (r.get("data") or {}).get("alert_id") == aid
    ]
    responses = [
        r for r in svc.repo("crew_paging_responses").list(
            tenant_id=current.tenant_id, limit=50
        )
        if (r.get("data") or {}).get("alert_id") == aid
    ]
    audit = [
        e for e in svc.repo("crew_paging_audit_events").list(
            tenant_id=current.tenant_id, limit=100
        )
        if (e.get("data") or {}).get("alert_id") == aid
    ]

    return {
        "alert": alert,
        "recipients": recipients,
        "responses": responses,
        "audit_trail": audit,
    }


# ── Push Delivery Callbacks ───────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/push/sent")
async def push_sent_callback(
    alert_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """FCM/APNs push sent callback. Records delivery attempt."""
    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.record_push_sent(
        alert_id=alert_id,
        recipient_id=payload["recipient_id"],
        push_message_id=payload.get("push_message_id", ""),
        platform=payload.get("platform", "unknown"),
        correlation_id=corr,
    )


@router.post("/alerts/{alert_id}/push/delivered")
async def push_delivered_callback(
    alert_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """FCM/APNs delivery receipt callback. Records device receipt."""
    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.record_push_delivered(
        alert_id=alert_id,
        recipient_id=payload["recipient_id"],
        push_message_id=payload.get("push_message_id", ""),
        correlation_id=corr,
    )


# ── Crew Response ─────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/respond")
async def crew_respond(
    alert_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Record crew member response to a page.
    response: ACKNOWLEDGE | ACCEPT | DECLINE
    """
    response_str = payload.get("response", "").upper()
    try:
        response = CrewResponse(response_str)
    except ValueError:
        return {"error": f"Invalid response. Must be one of: {[r.value for r in CrewResponse]}"}

    crew_member_id = payload.get("crew_member_id")
    if not crew_member_id:
        return {"error": "crew_member_id_required"}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.record_crew_response(
        alert_id=alert_id,
        crew_member_id=crew_member_id,
        response=response,
        decline_reason=payload.get("decline_reason"),
        location=payload.get("location"),
        correlation_id=corr,
    )


# ── Escalation ────────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/escalate")
async def escalate_alert(
    alert_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Escalate a paging alert (manual or timer-triggered).
    Optionally pages backup crew.
    """
    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.escalate_alert(
        alert_id=alert_id,
        escalation_reason=payload.get("reason", "MANUAL_ESCALATION"),
        triggered_by=payload.get("triggered_by", "DISPATCHER"),
        backup_crew_ids=payload.get("backup_crew_ids"),
        correlation_id=corr,
    )


@router.get("/escalation/check")
async def check_escalation_timers(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Check all active alerts for escalation timer violations. Used by background worker."""
    engine = _engine(db, current)
    return {"needs_escalation": engine.check_escalation_timers()}


# ── Device Registration ───────────────────────────────────────────────────────

@router.post("/devices/register")
async def register_device(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Register a crew member's push device (Android/iOS)."""
    required = ["crew_member_id", "push_token", "platform"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "fields": missing}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    record = await svc.create(
        table="crew_push_devices",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **payload,
            "registered_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "active": True,
        },
        correlation_id=corr,
    )
    return record


@router.get("/devices")
async def list_devices(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """List all registered push devices for this tenant."""
    svc = _svc(db)
    return svc.repo("crew_push_devices").list(
        tenant_id=current.tenant_id, limit=500
    )


# ── Crew Status Updates ───────────────────────────────────────────────────────

@router.post("/crew/status")
async def crew_status_update(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Record a crew status update (EN_ROUTE, ON_SCENE, AVAILABLE, etc.)."""
    crew_member_id = payload.get("crew_member_id")
    status = payload.get("status")
    if not crew_member_id or not status:
        return {"error": "crew_member_id and status required"}

    corr = getattr(request.state, "correlation_id", None)
    engine = _engine(db, current)
    return await engine.update_crew_status(
        crew_member_id=crew_member_id,
        status=status,
        unit_id=payload.get("unit_id"),
        location=payload.get("location"),
        correlation_id=corr,
    )


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/alerts/{alert_id}/audit")
async def alert_audit(
    alert_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Return full audit trail for a paging alert."""
    svc = _svc(db)
    audit = [
        e for e in svc.repo("crew_paging_audit_events").list(
            tenant_id=current.tenant_id, limit=200
        )
        if (e.get("data") or {}).get("alert_id") == alert_id
    ]
    return {"alert_id": alert_id, "audit_events": audit}
