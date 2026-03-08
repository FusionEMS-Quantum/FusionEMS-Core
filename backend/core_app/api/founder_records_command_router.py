"""Founder records/media command center router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.schemas.auth import CurrentUser
from core_app.schemas.founder_command_domains import RecordExportResponse, RecordsCommandSummary
from core_app.services.founder_command_domain_service import FounderCommandDomainService

router = APIRouter(
    prefix="/api/v1/founder/records-command",
    tags=["Founder Records Command"],
)


@router.get("/summary", response_model=RecordsCommandSummary)
def get_records_command_summary(
    _current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> RecordsCommandSummary:
    svc = FounderCommandDomainService(db)
    return svc.get_records_command_summary()


@router.get("/failed-exports", response_model=list[RecordExportResponse])
def list_failed_exports(
    limit: int = Query(default=50, ge=1, le=250),
    _current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[RecordExportResponse]:
    svc = FounderCommandDomainService(db)
    exports = svc.list_failed_record_exports(limit=limit)
    return [RecordExportResponse.model_validate(exp) for exp in exports]
