"""Platform Incident Router — incident lifecycle management API.

Provides CRUD + state machine transitions for platform incidents.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core_app.api.dependencies import get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.incident_state_machine import (
    IncidentSeverity,
    IncidentState,
    IncidentTransitionError,
    get_incident_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/platform/incidents", tags=["Platform Incidents"])


class CreateIncidentRequest(BaseModel):
    title: str
    severity: IncidentSeverity
    source: str = ""
    description: str = ""


class TransitionRequest(BaseModel):
    target_state: IncidentState
    note: str = ""


@router.post("")
async def create_incident(
    body: CreateIncidentRequest,
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    svc = get_incident_service()
    incident = svc.create(
        tenant_id=current.tenant_id,
        title=body.title,
        severity=body.severity,
        source=body.source,
        description=body.description,
    )
    return incident.model_dump()


@router.get("")
async def list_incidents(
    active_only: bool = True,
    current: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    svc = get_incident_service()
    if active_only:
        incidents = svc.list_active(current.tenant_id)
    else:
        incidents = svc.list_all(current.tenant_id)
    return [i.model_dump() for i in incidents]


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    svc = get_incident_service()
    incident = svc.get(incident_id)
    if not incident or incident.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@router.post("/{incident_id}/transition")
async def transition_incident(
    incident_id: str,
    body: TransitionRequest,
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    svc = get_incident_service()
    incident = svc.get(incident_id)
    if not incident or incident.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        updated = svc.transition(
            incident_id=incident_id,
            target_state=body.target_state,
            actor=current.user_id,
            note=body.note,
        )
    except IncidentTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return updated.model_dump()
