"""Founder specialty operations command center router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_founder_only_audited
from core_app.schemas.auth import CurrentUser
from core_app.schemas.founder_command_domains import FlightMissionResponse, SpecialtyOpsSummary
from core_app.services.founder_command_domain_service import FounderCommandDomainService

router = APIRouter(
    prefix="/api/v1/founder/specialty-ops-command",
    tags=["Founder Specialty Ops Command"],
)

_FOUNDER = Depends(require_founder_only_audited())


@router.get("/summary", response_model=SpecialtyOpsSummary)
def get_specialty_ops_summary(
    _current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> SpecialtyOpsSummary:
    svc = FounderCommandDomainService(db)
    return svc.get_specialty_ops_summary()


@router.get("/pending-flight-missions", response_model=list[FlightMissionResponse])
def list_pending_flight_missions(
    limit: int = Query(default=50, ge=1, le=250),
    _current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[FlightMissionResponse]:
    svc = FounderCommandDomainService(db)
    missions = svc.list_pending_flight_missions(limit=limit)
    return [FlightMissionResponse.model_validate(mission) for mission in missions]
