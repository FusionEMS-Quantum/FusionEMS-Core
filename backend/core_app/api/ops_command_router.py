"""
Ops Command Center Router — FusionEMS-Core
Founder operations command: unified view of all operational domains,
AI issue analysis, top 3 next actions, and ops health summary.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.cad.dispatch_engine import DispatchEngine
from core_app.fleet.fault_detector import FaultDetector
from core_app.fleet.readiness_engine import ReadinessEngine
from core_app.ops.ai_assistant import OpsAIAssistant
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.staffing.readiness_engine import StaffingReadinessEngine

router = APIRouter(prefix="/api/v1/ops", tags=["Ops Command"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


# ── Full Ops Command Summary ──────────────────────────────────────────────────

@router.get("/command")
async def ops_command(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Founder Operations Command Center.
    Returns full ops status: missions, pages, fleet, staffing,
    AI issues, and top 3 next actions.
    """
    pub = get_event_publisher()

    # Gather from all domains
    dispatch_engine = DispatchEngine(db, pub, current.tenant_id, current.user_id)
    fleet_engine = ReadinessEngine(db, pub, current.tenant_id, current.user_id)
    staffing_engine = StaffingReadinessEngine(db, pub, current.tenant_id, current.user_id)
    ai = OpsAIAssistant()

    ops_board = dispatch_engine.get_ops_board()
    fleet_summary = fleet_engine.fleet_summary()
    staffing_summary = staffing_engine.staffing_readiness_summary()

    svc = _svc(db)
    fleet_alerts = svc.repo("fleet_alerts").list(tenant_id=current.tenant_id, limit=50)
    facility_requests = svc.repo("dispatch_requests").list(tenant_id=current.tenant_id, limit=50)

    # AI Issues
    ai_issues: list[dict] = []

    for m in ops_board.get("unassigned_missions") or []:
        ai_issues.append(ai.explain_unassigned_mission(m))

    for p in ops_board.get("escalated_pages") or []:
        ai_issues.append(ai.explain_escalated_page(p))

    for gap in staffing_summary.get("staffing_gaps") or []:
        ai_issues.append(ai.explain_staffing_gap(gap))

    for alert in fleet_alerts[:3]:
        adata = alert.get("data") or {}
        if not adata.get("resolved") and not adata.get("acknowledged"):
            ai_issues.append(ai.explain_fleet_alert(alert))

    # Sort issues by severity
    severity_order = {"BLOCKING": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}
    ai_issues.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 99))

    top_actions = ai.generate_top_actions(ops_board)

    # Overall ops health color
    if any(i.get("severity") == "BLOCKING" for i in ai_issues):
        ops_health = "RED"
    elif any(i.get("severity") == "HIGH" for i in ai_issues):
        ops_health = "ORANGE"
    elif any(i.get("severity") == "MEDIUM" for i in ai_issues):
        ops_health = "YELLOW"
    else:
        ops_health = "GREEN"

    # Pending facility requests
    pending_facility = [
        r for r in facility_requests
        if (r.get("data") or {}).get("state") in ("REQUEST_CREATED", "REQUEST_VALIDATED")
    ]

    return {
        "ops_health": ops_health,
        "top_3_actions": top_actions,
        "ai_issues": ai_issues,
        "dispatch": {
            "active_mission_count": ops_board.get("active_mission_count", 0),
            "unassigned_count": ops_board.get("unassigned_count", 0),
            "en_route_count": ops_board.get("en_route_count", 0),
            "active_missions": ops_board.get("active_missions") or [],
            "unassigned_missions": ops_board.get("unassigned_missions") or [],
        },
        "crewlink": {
            "escalated_page_count": ops_board.get("escalated_page_count", 0),
            "late_page_count": ops_board.get("late_page_count", 0),
            "escalated_pages": ops_board.get("escalated_pages") or [],
            "late_pages": ops_board.get("late_pages") or [],
        },
        "fleet": {
            "fleet_count": fleet_summary.get("fleet_count", 0),
            "avg_readiness": fleet_summary.get("avg_readiness", 0),
            "units_ready": fleet_summary.get("units_ready", 0),
            "units_limited": fleet_summary.get("units_limited", 0),
            "units_no_go": fleet_summary.get("units_no_go", 0),
            "active_fleet_alerts": len([
                a for a in fleet_alerts
                if not (a.get("data") or {}).get("resolved")
            ]),
        },
        "staffing": {
            "available": staffing_summary.get("available", 0),
            "assigned": staffing_summary.get("assigned", 0),
            "unavailable": staffing_summary.get("unavailable", 0),
            "fatigue_flags": staffing_summary.get("fatigue_flags", 0),
            "active_conflicts": staffing_summary.get("active_conflicts", 0),
            "overall_readiness": staffing_summary.get("overall_readiness", "UNKNOWN"),
            "gaps": staffing_summary.get("staffing_gaps") or [],
        },
        "facility_requests": {
            "pending_count": len(pending_facility),
            "pending": pending_facility[:5],
        },
        "computed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


# ── AI Issue Analysis ─────────────────────────────────────────────────────────

@router.post("/ai/analyze-mission")
async def analyze_mission(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI analysis of a specific mission issue."""
    ai = OpsAIAssistant()
    issue_type = payload.get("issue_type", "unassigned")
    mission_data = payload.get("mission_data") or {}

    if issue_type == "unassigned":
        return ai.explain_unassigned_mission({"data": mission_data})
    elif issue_type == "late_transport":
        return ai.explain_late_transport({"data": mission_data})
    elif issue_type == "oos_unit":
        return ai.explain_out_of_service_unit({"data": mission_data})
    return {"error": "unknown_issue_type"}


@router.post("/ai/analyze-page")
async def analyze_page(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI analysis of a specific paging issue."""
    ai = OpsAIAssistant()
    return ai.explain_escalated_page({"data": payload.get("alert_data") or {}})


@router.post("/ai/analyze-fleet")
async def analyze_fleet(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI analysis of a fleet alert."""
    ai = OpsAIAssistant()
    return ai.explain_fleet_alert({"data": payload.get("alert_data") or {}})


@router.post("/ai/analyze-staffing")
async def analyze_staffing(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI analysis of a staffing gap."""
    ai = OpsAIAssistant()
    return ai.explain_staffing_gap(payload.get("gap") or {})


# ── Telemetry Ingestion ───────────────────────────────────────────────────────

@router.post("/telemetry/ingest")
async def ingest_telemetry(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Ingest vehicle telemetry event (OBD-II, GPS, engine health).
    Runs fault detection and creates fleet alerts if needed.
    Idempotent — safe to retry with same correlation_id.
    """
    unit_id = payload.get("unit_id")
    if not unit_id:
        return {"error": "unit_id_required"}

    corr = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    # Store raw telemetry event
    event = await svc.create(
        table="vehicle_telemetry_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "unit_id": unit_id,
            "payload": payload.get("payload") or {},
            "source": payload.get("source", "OBD2"),
            "ingested_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
        correlation_id=corr,
    )

    # Run fault detection
    pub = get_event_publisher()
    detector = FaultDetector(db, pub, current.tenant_id, current.user_id)
    obd_payload = payload.get("payload") or {}
    faults = detector.analyze_obd_reading(uuid.UUID(unit_id), obd_payload)

    alerts_created = []
    for fault in faults:
        if fault.get("severity") in ("critical", "warning"):
            alert = await svc.create(
                table="fleet_alerts",
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                data={
                    "unit_id": unit_id,
                    "severity": fault.get("severity"),
                    "message": fault.get("message"),
                    "fault_type": fault.get("fault_type"),
                    "value": fault.get("value"),
                    "threshold": fault.get("threshold"),
                    "resolved": False,
                    "acknowledged": False,
                    "telemetry_event_id": str(event["id"]),
                },
                correlation_id=corr,
            )
            alerts_created.append(str(alert["id"]))

    return {
        "telemetry_event_id": str(event["id"]),
        "faults_detected": len(faults),
        "alerts_created": alerts_created,
        "unit_id": unit_id,
    }


@router.post("/telemetry/health-snapshot")
async def vehicle_health_snapshot(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Store a vehicle health snapshot."""
    unit_id = payload.get("unit_id")
    if not unit_id:
        return {"error": "unit_id_required"}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="vehicle_health_snapshots",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**payload, "snapshot_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()},
        correlation_id=corr,
    )


# ── Vehicle Inspection ────────────────────────────────────────────────────────

@router.post("/inspections")
async def create_inspection(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Record a pre-shift or post-shift vehicle inspection."""
    required = ["unit_id", "inspection_type", "inspector_id"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "fields": missing}

    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="vehicle_inspection_records",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **payload,
            "inspected_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
        correlation_id=corr,
    )


# ── Fault Codes ───────────────────────────────────────────────────────────────

@router.post("/fault-codes")
async def record_fault_code(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Record a vehicle fault code (DTC)."""
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="vehicle_fault_codes",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **payload,
            "recorded_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
        correlation_id=corr,
    )


# ── Fleet Audit ───────────────────────────────────────────────────────────────

@router.get("/fleet/audit")
async def fleet_audit(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 100,
):
    """Return fleet audit events."""
    svc = _svc(db)
    return svc.repo("fleet_audit_events").list(
        tenant_id=current.tenant_id, limit=limit
    )


# ── Deployment Run Visibility (Zero-Error Onboarding) ─────────────────────────

@router.get("/deployment-runs")
async def list_deployment_runs(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 50,
    state: str = "",
):
    """
    Founder visibility into all agency deployment/provisioning runs.
    Shows the zero-error deployment state machine status for every signup.
    """
    from sqlalchemy import text as sa_text

    where = "WHERE 1=1"
    params: dict = {"limit": limit}
    if state:
        where += " AND current_state = :state"
        params["state"] = state

    rows = db.execute(
        sa_text(
            f"SELECT id, external_event_id, agency_id, current_state, "
            f"failure_reason, retry_count, metadata_blob, created_at, updated_at "
            f"FROM deployment_runs "
            f"{where} "
            f"ORDER BY created_at DESC LIMIT :limit"
        ),
        params,
    ).mappings().all()

    return [dict(r) for r in rows]


@router.get("/deployment-runs/{run_id}/steps")
async def get_deployment_steps(
    run_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Full step-by-step audit trail for a single deployment run.
    Every provisioning action is recorded here.
    """
    from sqlalchemy import text as sa_text

    run = db.execute(
        sa_text(
            "SELECT id, external_event_id, agency_id, current_state, "
            "failure_reason, retry_count, metadata_blob, created_at, updated_at "
            "FROM deployment_runs WHERE id = :run_id"
        ),
        {"run_id": run_id},
    ).mappings().first()

    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Deployment run not found")

    steps = db.execute(
        sa_text(
            "SELECT id, step_name, status, result_blob, error_message, "
            "created_at FROM deployment_steps "
            "WHERE run_id = :run_id ORDER BY created_at ASC"
        ),
        {"run_id": run_id},
    ).mappings().all()

    return {
        "run": dict(run),
        "steps": [dict(s) for s in steps],
    }
