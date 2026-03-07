from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.audit_log import AuditLog
from core_app.models.governance import AuditEventDomain, AuditRetentionPolicy, AuditSnapshot
from core_app.repositories.audit_repository import AuditRepository
from core_app.schemas.audit import AuditLogResponse, AuditMutationRequest
from core_app.schemas.auth import CurrentUser
from core_app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])

_ADMIN_ROLES = frozenset({"founder", "agency_admin", "compliance"})


# ─── Additional response schemas ─────────────────────────────────────────────

class AuditSearchParams(BaseModel):
    action: str | None = None
    entity_name: str | None = None
    actor_user_id: UUID | None = None
    domain: AuditEventDomain | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    limit: int = 100
    offset: int = 0


class AuditSnapshotCreate(BaseModel):
    snapshot_type: str
    entity_name: str
    entity_id: UUID
    snapshot_data: dict[str, Any]
    reason: str | None = None


class AuditSnapshotResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    snapshot_type: str
    entity_name: str
    entity_id: UUID
    snapshot_data: dict[str, Any]
    captured_by_user_id: UUID | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RetentionPolicyCreate(BaseModel):
    domain: AuditEventDomain
    retention_days: int = 2555
    archive_after_days: int = 365
    is_regulatory_hold: bool = False
    hold_reason: str | None = None


class RetentionPolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    domain: AuditEventDomain
    retention_days: int
    archive_after_days: int
    is_regulatory_hold: bool
    hold_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Basic log endpoints ──────────────────────────────────────────────────────

@router.get("/logs", response_model=list[AuditLogResponse])
def list_logs(
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AuditLogResponse]:
    rows = AuditRepository(db).list_for_tenant(current_user.tenant_id)
    return [AuditLogResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "/logs", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED
)
def create_audit_log(
    payload: AuditMutationRequest,
    request: Request,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditLogResponse:
    service = AuditService(db)
    row = service.log_mutation(
        tenant_id=current_user.tenant_id,
        action=payload.action,
        entity_name=payload.entity_name,
        entity_id=payload.entity_id,
        actor_user_id=current_user.user_id,
        field_changes=payload.field_changes,
        correlation_id=request.state.correlation_id,
    )
    db.commit()
    return AuditLogResponse.model_validate(row, from_attributes=True)


# ─── Advanced search ──────────────────────────────────────────────────────────

@router.post("/logs/search", response_model=list[AuditLogResponse])
def search_audit_logs(
    params: AuditSearchParams,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AuditLogResponse]:
    """
    Advanced audit log search with date range, action, entity, and actor filters.
    Restricted to admin/compliance roles.
    """
    if current_user.role not in _ADMIN_ROLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient privileges to search audit logs")

    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == current_user.tenant_id)
    )
    if params.action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{params.action}%"))
    if params.entity_name:
        stmt = stmt.where(AuditLog.entity_name.ilike(f"%{params.entity_name}%"))
    if params.actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == params.actor_user_id)
    if params.from_dt:
        stmt = stmt.where(AuditLog.created_at >= params.from_dt)
    if params.to_dt:
        stmt = stmt.where(AuditLog.created_at <= params.to_dt)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(params.limit).offset(params.offset)
    rows = db.scalars(stmt).all()
    return [AuditLogResponse.model_validate(r, from_attributes=True) for r in rows]


# ─── Audit snapshots ──────────────────────────────────────────────────────────

@router.post("/snapshots", response_model=AuditSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    payload: AuditSnapshotCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> AuditSnapshotResponse:
    """Capture a point-in-time compliance snapshot of any entity."""
    if current_user.role not in _ADMIN_ROLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    snap = AuditSnapshot(
        tenant_id=current_user.tenant_id,
        snapshot_type=payload.snapshot_type,
        entity_name=payload.entity_name,
        entity_id=payload.entity_id,
        snapshot_data=payload.snapshot_data,
        captured_by_user_id=current_user.user_id,
        reason=payload.reason,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return AuditSnapshotResponse.model_validate(snap)


@router.get("/snapshots", response_model=list[AuditSnapshotResponse])
def list_snapshots(
    entity_name: str | None = None,
    entity_id: UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[AuditSnapshotResponse]:
    if current_user.role not in _ADMIN_ROLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    stmt = select(AuditSnapshot).where(AuditSnapshot.tenant_id == current_user.tenant_id)
    if entity_name:
        stmt = stmt.where(AuditSnapshot.entity_name == entity_name)
    if entity_id:
        stmt = stmt.where(AuditSnapshot.entity_id == entity_id)
    stmt = stmt.order_by(AuditSnapshot.created_at.desc()).limit(200)
    rows = db.scalars(stmt).all()
    return [AuditSnapshotResponse.model_validate(r) for r in rows]


# ─── Retention policies ────────────────────────────────────────────────────────

@router.get("/retention", response_model=list[RetentionPolicyResponse])
def list_retention_policies(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[RetentionPolicyResponse]:
    rows = db.scalars(
        select(AuditRetentionPolicy)
        .where(AuditRetentionPolicy.tenant_id == current_user.tenant_id)
        .order_by(AuditRetentionPolicy.domain)
    ).all()
    return [RetentionPolicyResponse.model_validate(r) for r in rows]


@router.put("/retention/{domain}", response_model=RetentionPolicyResponse)
def upsert_retention_policy(
    domain: AuditEventDomain,
    payload: RetentionPolicyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> RetentionPolicyResponse:
    """Upsert retention policy for an audit event domain. Founder/admin only."""
    if current_user.role not in frozenset({"founder", "agency_admin"}):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    existing = db.scalar(
        select(AuditRetentionPolicy).where(
            AuditRetentionPolicy.tenant_id == current_user.tenant_id,
            AuditRetentionPolicy.domain == domain,
        )
    )
    if existing:
        existing.retention_days = payload.retention_days
        existing.archive_after_days = payload.archive_after_days
        existing.is_regulatory_hold = payload.is_regulatory_hold
        existing.hold_reason = payload.hold_reason
        policy = existing
    else:
        policy = AuditRetentionPolicy(
            tenant_id=current_user.tenant_id,
            domain=domain,
            retention_days=payload.retention_days,
            archive_after_days=payload.archive_after_days,
            is_regulatory_hold=payload.is_regulatory_hold,
            hold_reason=payload.hold_reason,
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)
    return RetentionPolicyResponse.model_validate(policy)

