from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/fire/ops", tags=["Fire"])


@router.post("/incidents")
async def create_incident(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="fire_incidents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/incidents")
async def list_incidents(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 200,
    offset: int = 0,
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("fire_incidents").list(
        tenant_id=current.tenant_id,
        limit=limit,
        offset=offset,
    )


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("fire_incidents").get(
        tenant_id=current.tenant_id,
        record_id=incident_id,
    )
    if rec is None:
        return {"error": "incident_not_found"}
    return rec


@router.post("/incidents/{incident_id}/assign")
async def assign(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    data = {"incident_id": str(incident_id), **payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="fire_personnel_assignments",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/ops/board")
async def ops_board(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 200,
):
    svc = DominationService(db, get_event_publisher())
    return {
        "fire_incidents": svc.repo("fire_incidents").list(
            tenant_id=current.tenant_id, limit=limit, offset=0
        )
    }


@router.post("/preplans")
async def create_preplan(
    payload: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fire_preplans",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.get("/preplans")
async def list_preplans(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("fire_preplans").list(tenant_id=current.tenant_id, limit=500)


@router.post("/hydrants")
async def create_hydrant(
    payload: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fire_hydrants",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.get("/hydrants")
async def list_hydrants(
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float = 1.0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    hydrants = svc.repo("fire_hydrants").list(tenant_id=current.tenant_id, limit=5000)
    if lat and lng:

        def _dist(h):
            hlat = h["data"].get("lat", 0)
            hlng = h["data"].get("lng", 0)
            dlat = (hlat - lat) * 69
            dlng = (hlng - lng) * 54.6
            return (dlat**2 + dlng**2) ** 0.5

        hydrants = [h for h in hydrants if _dist(h) <= radius_miles]
    return hydrants


# ── NERIS Export ──────────────────────────────────────────────────────────


@router.post("/neris/validate/{incident_id}")
async def validate_neris(
    incident_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    inc = svc.repo("fire_incidents").get(
        tenant_id=current.tenant_id, record_id=incident_id
    )
    if inc is None:
        return {"error": "incident_not_found"}
    data = inc.get("data", {})
    issues: list[dict[str, str]] = []
    for field in (
        "neris_incident_type_code",
        "incident_date",
        "alarm_date",
        "arrival_date",
        "street_address",
        "city",
        "state",
        "zip_code",
    ):
        if not data.get(field):
            issues.append({"field": field, "section": "A", "severity": "error", "message": f"Required field '{field}' is missing"})
    if not data.get("narrative"):
        issues.append({"field": "narrative", "section": "supplement", "severity": "warning", "message": "Narrative recommended"})
    return {"incident_id": str(incident_id), "issues": issues, "valid": not any(i["severity"] == "error" for i in issues)}


@router.post("/neris/export")
async def create_neris_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    incident_ids = payload.get("incident_ids", [])
    if not incident_ids:
        return {"error": "no_incidents_specified"}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="neris_export_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "incident_ids": incident_ids,
            "state": "PENDING",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/neris/exports")
async def list_neris_exports(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("neris_export_jobs").list(tenant_id=current.tenant_id, limit=100)


# ── Inspections ───────────────────────────────────────────────────────────


@router.post("/inspections")
async def create_inspection(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="fire_inspections",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/inspections")
async def list_inspections(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("fire_inspections").list(tenant_id=current.tenant_id, limit=500)


# ── Apparatus ─────────────────────────────────────────────────────────────


@router.post("/incidents/{incident_id}/apparatus")
async def add_apparatus(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    data = {"incident_id": str(incident_id), **payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="fire_apparatus_records",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
