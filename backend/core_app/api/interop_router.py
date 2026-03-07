from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.governance import (
    ExternalIdentifier,
    HandoffExchangeRecord,
    HandoffExchangeStatus,
    InteropExportRecord,
    InteropImportRecord,
    InteropMappingRule,
    InteropPayload,
    InteropPayloadStatus,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.interop_service import InteropService

router = APIRouter(prefix="/interop", tags=["interop"])

_ADMIN_ROLES = frozenset({"founder", "agency_admin"})
_CLINICAL_ROLES = frozenset({"founder", "agency_admin", "ems", "clinical_provider"})


# ─── Request / Response schemas ──────────────────────────────────────────────

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


class ExternalIdentifierCreate(BaseModel):
    entity_type: str
    entity_id: UUID
    system_uri: str
    identifier_value: str
    identifier_type: str | None = None
    is_primary: bool = False


class ExternalIdentifierResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID
    system_uri: str
    identifier_value: str
    identifier_type: str | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InteropMappingRuleCreate(BaseModel):
    source_system: str
    source_field: str
    target_entity: str
    target_field: str
    transform_expression: str | None = None
    default_value: str | None = None


class InteropMappingRuleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    source_system: str
    source_field: str
    target_entity: str
    target_field: str
    transform_expression: str | None = None
    default_value: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InteropPayloadIngest(BaseModel):
    source_system: str
    payload_type: str  # FHIR_BUNDLE, HL7V2, CSV, CUSTOM
    schema_version: str | None = None
    raw_payload: dict[str, Any]


class InteropPayloadResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    source_system: str
    payload_type: str
    schema_version: str | None = None
    status: InteropPayloadStatus
    validation_errors: dict[str, Any]
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HandoffAcknowledge(BaseModel):
    acknowledged_by: str
    note: str | None = None


class HandoffExchangeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    incident_id: UUID
    destination_facility: str
    exchange_type: str
    status: HandoffExchangeStatus
    payload_reference: str | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Handoff exchange ─────────────────────────────────────────────────────────

@router.post("/handoff", response_model=HandoffExchangeResponse, status_code=status.HTTP_201_CREATED)
def create_handoff_packet(
    payload: HandoffPacketCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> HandoffExchangeResponse:
    """Create a handoff exchange packet for a facility transfer."""
    if current.role not in _CLINICAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = InteropService(db)
    record = service.create_handoff_packet(
        tenant_id=current.tenant_id,
        incident_id=payload.incident_id,
        destination_facility=payload.destination_facility,
        exchange_type=payload.exchange_type,
        payload_reference=payload.payload_reference,
    )
    db.commit()
    db.refresh(record)
    return HandoffExchangeResponse.model_validate(record)


@router.get("/handoff", response_model=list[HandoffExchangeResponse])
def list_handoff_exchanges(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[HandoffExchangeResponse]:
    """Query handoff exchange history for the current tenant."""
    rows = db.scalars(
        select(HandoffExchangeRecord)
        .where(HandoffExchangeRecord.tenant_id == current.tenant_id)
        .order_by(HandoffExchangeRecord.created_at.desc())
        .limit(200)
    ).all()
    return [HandoffExchangeResponse.model_validate(r) for r in rows]


@router.post("/handoff/{exchange_id}/acknowledge", response_model=HandoffExchangeResponse)
def acknowledge_handoff(
    exchange_id: UUID,
    payload: HandoffAcknowledge,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> HandoffExchangeResponse:
    """Record recipient acknowledgment of a handoff exchange."""
    record = db.scalar(
        select(HandoffExchangeRecord).where(
            HandoffExchangeRecord.id == exchange_id,
            HandoffExchangeRecord.tenant_id == current.tenant_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Handoff exchange not found")

    from datetime import UTC
    record.status = HandoffExchangeStatus.ACKNOWLEDGED
    record.acknowledged_at = datetime.now(UTC)
    record.acknowledged_by = payload.acknowledged_by
    db.commit()
    db.refresh(record)
    return HandoffExchangeResponse.model_validate(record)


# ─── External identifiers ─────────────────────────────────────────────────────

@router.post("/external-identifiers", response_model=ExternalIdentifierResponse, status_code=status.HTTP_201_CREATED)
def create_external_identifier(
    payload: ExternalIdentifierCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> ExternalIdentifierResponse:
    """Register an external system identifier for an internal entity."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    ext_id = ExternalIdentifier(
        tenant_id=current.tenant_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        system_uri=payload.system_uri,
        identifier_value=payload.identifier_value,
        identifier_type=payload.identifier_type,
        is_primary=payload.is_primary,
    )
    db.add(ext_id)
    db.commit()
    db.refresh(ext_id)
    return ExternalIdentifierResponse.model_validate(ext_id)


@router.get("/external-identifiers/{entity_type}/{entity_id}", response_model=list[ExternalIdentifierResponse])
def get_external_identifiers(
    entity_type: str,
    entity_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ExternalIdentifierResponse]:
    """Retrieve all external identifiers for a specific entity."""
    rows = db.scalars(
        select(ExternalIdentifier).where(
            ExternalIdentifier.tenant_id == current.tenant_id,
            ExternalIdentifier.entity_type == entity_type,
            ExternalIdentifier.entity_id == entity_id,
        )
    ).all()
    return [ExternalIdentifierResponse.model_validate(r) for r in rows]


@router.get("/external-identifiers/mappings/{system_uri}", response_model=list[ExternalIdentifierResponse])
def get_mappings_for_system(
    system_uri: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ExternalIdentifierResponse]:
    """Query all external identifiers registered for a specific external system."""
    rows = db.scalars(
        select(ExternalIdentifier).where(
            ExternalIdentifier.tenant_id == current.tenant_id,
            ExternalIdentifier.system_uri == system_uri,
        ).limit(500)
    ).all()
    return [ExternalIdentifierResponse.model_validate(r) for r in rows]


# ─── Mapping rules ────────────────────────────────────────────────────────────

@router.post("/mapping-rules", response_model=InteropMappingRuleResponse, status_code=status.HTTP_201_CREATED)
def create_mapping_rule(
    payload: InteropMappingRuleCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> InteropMappingRuleResponse:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    rule = InteropMappingRule(
        tenant_id=current.tenant_id,
        source_system=payload.source_system,
        source_field=payload.source_field,
        target_entity=payload.target_entity,
        target_field=payload.target_field,
        transform_expression=payload.transform_expression,
        default_value=payload.default_value,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return InteropMappingRuleResponse.model_validate(rule)


@router.get("/mapping-rules/{source_system}", response_model=list[InteropMappingRuleResponse])
def list_mapping_rules(
    source_system: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[InteropMappingRuleResponse]:
    rows = db.scalars(
        select(InteropMappingRule).where(
            InteropMappingRule.tenant_id == current.tenant_id,
            InteropMappingRule.source_system == source_system,
            InteropMappingRule.is_active == True,  # noqa: E712
        )
    ).all()
    return [InteropMappingRuleResponse.model_validate(r) for r in rows]


# ─── Payload ingestion ────────────────────────────────────────────────────────

@router.post("/payloads", response_model=InteropPayloadResponse, status_code=status.HTTP_201_CREATED)
def ingest_payload(
    payload: InteropPayloadIngest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> InteropPayloadResponse:
    """Ingest an external payload for validation and transformation."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    record = InteropPayload(
        tenant_id=current.tenant_id,
        source_system=payload.source_system,
        payload_type=payload.payload_type,
        schema_version=payload.schema_version,
        raw_payload=payload.raw_payload,
        status=InteropPayloadStatus.RECEIVED,
        validation_errors={},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return InteropPayloadResponse.model_validate(record)


@router.post("/validate/{entity_type}", status_code=status.HTTP_200_OK)
def validate_canonical(
    entity_type: str,
    payload: dict,
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Validate a payload against the canonical data contract for the given entity type.
    Returns a validation report with any constraint violations.
    """
    _ = current  # auth gate: request must be authenticated and tenant-scoped
    errors: list[str] = []
    required_fields_by_type: dict[str, list[str]] = {
        "patient": ["first_name", "last_name", "date_of_birth"],
        "incident": ["incident_number", "dispatch_time", "status"],
        "encounter": ["incident_id", "status"],
    }
    required = required_fields_by_type.get(entity_type, [])
    for field in required:
        if field not in payload or payload[field] is None:
            errors.append(f"Required field missing or null: {field}")

    return {
        "entity_type": entity_type,
        "valid": len(errors) == 0,
        "errors": errors,
        "error_count": len(errors),
    }


# ─── Provenance ───────────────────────────────────────────────────────────────

@router.post("/provenance")
def record_provenance(
    payload: ImportProvenanceCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Record import provenance for externally sourced data."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = InteropService(db)
    record = service.record_import_provenance(
        tenant_id=current.tenant_id,
        entity_name=payload.entity_name,
        entity_id=payload.entity_id,
        source_system=payload.source_system,
        external_id=payload.external_id,
        raw_payload=payload.raw_payload,
    )
    db.commit()
    return {"id": str(record.id), "status": "recorded"}


@router.get("/provenance/{entity_type}/{entity_id}")
def get_provenance_lineage(
    entity_type: str,
    entity_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Trace data lineage for a given entity — show all external sources and transformations."""
    from core_app.models.governance import DataProvenance
    rows = db.scalars(
        select(DataProvenance).where(
            DataProvenance.tenant_id == current.tenant_id,
            DataProvenance.entity_name == entity_type,
            DataProvenance.entity_id == entity_id,
        ).order_by(DataProvenance.imported_at.desc())
    ).all()

    ext_ids = db.scalars(
        select(ExternalIdentifier).where(
            ExternalIdentifier.tenant_id == current.tenant_id,
            ExternalIdentifier.entity_type == entity_type,
            ExternalIdentifier.entity_id == entity_id,
        )
    ).all()

    return {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "provenance_records": [
            {
                "id": str(r.id),
                "source_system": r.source_system,
                "external_id": r.external_id,
                "imported_at": r.imported_at.isoformat(),
            }
            for r in rows
        ],
        "external_identifiers": [
            {
                "system_uri": e.system_uri,
                "identifier_value": e.identifier_value,
                "identifier_type": e.identifier_type,
                "is_primary": e.is_primary,
            }
            for e in ext_ids
        ],
    }


# ─── Import / Export records ──────────────────────────────────────────────────

@router.get("/import-records", response_model=list[dict])
def list_import_records(
    source_system: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[dict]:
    stmt = select(InteropImportRecord).where(
        InteropImportRecord.tenant_id == current.tenant_id
    )
    if source_system:
        stmt = stmt.where(InteropImportRecord.source_system == source_system)
    stmt = stmt.order_by(InteropImportRecord.created_at.desc()).limit(200)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "source_system": r.source_system,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "status": r.status,
            "warnings": r.warnings,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/export-records", response_model=list[dict])
def list_export_records(
    destination_system: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[dict]:
    stmt = select(InteropExportRecord).where(
        InteropExportRecord.tenant_id == current.tenant_id
    )
    if destination_system:
        stmt = stmt.where(InteropExportRecord.destination_system == destination_system)
    stmt = stmt.order_by(InteropExportRecord.created_at.desc()).limit(200)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id),
            "destination_system": r.destination_system,
            "export_format": r.export_format,
            "status": r.status,
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
        }
        for r in rows
    ]
