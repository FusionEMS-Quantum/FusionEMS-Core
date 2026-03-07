from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.interop_service import InteropService

router = APIRouter(prefix="/interop", tags=["interop"])


class HandoffPacketCreate(BaseModel):
    incident_id: UUID
    destination_facility: str
    exchange_type: str
    payload_reference: str | None = None


class ImportProvenanceCreate(BaseModel):
    entity_name: str
    entity_id: UUID
    source_system: str
    external_id: str
    raw_payload: dict[str, Any] | None = None


@router.post("/handoff")
def create_handoff_packet(
    payload: HandoffPacketCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Create a handoff exchange packet for a facility transfer."""
    if current.role not in ["founder", "agency_admin", "ems", "clinical_provider"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = InteropService(db)
    return service.create_handoff_packet(
        tenant_id=current.tenant_id,
        incident_id=payload.incident_id,
        destination_facility=payload.destination_facility,
        exchange_type=payload.exchange_type,
        payload_reference=payload.payload_reference,
    )


@router.post("/provenance")
def record_provenance(
    payload: ImportProvenanceCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Record import provenance for externally sourced data."""
    if current.role not in ["founder", "agency_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = InteropService(db)
    return service.record_import_provenance(
        tenant_id=current.tenant_id,
        entity_name=payload.entity_name,
        entity_id=payload.entity_id,
        source_system=payload.source_system,
        external_id=payload.external_id,
        raw_payload=payload.raw_payload,
    )
