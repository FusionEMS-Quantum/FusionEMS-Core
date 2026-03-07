"""
Policy management router — full CRUD for TenantPolicy with versioning,
approval workflow, and audit trail for every mutation.
"""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.governance import (
    PolicyApproval,
    PolicyApprovalStatus,
    PolicyChangeAuditEvent,
    PolicyVersion,
    TenantPolicy,
)
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/policies", tags=["policies"])

_ADMIN_ROLES = frozenset({"founder", "agency_admin"})


# ─── Request / Response schemas ──────────────────────────────────────────────

class PolicyCreate(BaseModel):
    key: str
    value: dict
    change_reason: str | None = None


class PolicyUpdate(BaseModel):
    value: dict
    change_reason: str | None = None


class PolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    key: str
    value: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyVersionResponse(BaseModel):
    id: UUID
    policy_id: UUID
    version_number: int
    value_snapshot: dict
    changed_by_user_id: UUID
    change_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyApprovalCreate(BaseModel):
    proposed_value: dict


class PolicyApprovalResponse(BaseModel):
    id: UUID
    policy_id: UUID
    requested_by_user_id: UUID
    proposed_value: dict
    status: str
    reviewed_by_user_id: UUID | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyApprovalReview(BaseModel):
    reason: str | None = None


# ─── Policy CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[PolicyResponse])
def list_policies(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[PolicyResponse]:
    """List all active policies for the current tenant."""
    rows = db.scalars(
        select(TenantPolicy)
        .where(TenantPolicy.tenant_id == current.tenant_id, TenantPolicy.is_active == True)  # noqa: E712
        .order_by(TenantPolicy.key)
    ).all()
    return [PolicyResponse.model_validate(r) for r in rows]


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyResponse:
    policy = _get_policy_or_404(db, policy_id, current.tenant_id)
    return PolicyResponse.model_validate(policy)


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyResponse:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    # Unique key per tenant
    existing = db.scalar(
        select(TenantPolicy).where(
            TenantPolicy.tenant_id == current.tenant_id,
            TenantPolicy.key == payload.key,
            TenantPolicy.is_active == True,  # noqa: E712
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Policy key '{payload.key}' already exists")

    policy = TenantPolicy(
        tenant_id=current.tenant_id,
        key=payload.key,
        value=payload.value,
        version=1,
    )
    db.add(policy)
    db.flush()

    _snapshot_version(db, policy, current.user_id, payload.change_reason)
    _record_policy_audit(db, policy, "CREATE", None, payload.value, current.user_id)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: UUID,
    payload: PolicyUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyResponse:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    policy = _get_policy_or_404(db, policy_id, current.tenant_id)
    old_value = dict(policy.value)

    policy.value = payload.value
    policy.version = (policy.version or 0) + 1
    db.flush()

    _snapshot_version(db, policy, current.user_id, payload.change_reason)
    _record_policy_audit(db, policy, "UPDATE", old_value, payload.value, current.user_id)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_policy(
    policy_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> None:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    policy = _get_policy_or_404(db, policy_id, current.tenant_id)
    policy.is_active = False
    db.flush()
    _record_policy_audit(db, policy, "DEACTIVATE", dict(policy.value), policy.value, current.user_id)
    db.commit()


# ─── Policy version history ───────────────────────────────────────────────────

@router.get("/{policy_id}/versions", response_model=list[PolicyVersionResponse])
def list_policy_versions(
    policy_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[PolicyVersionResponse]:
    _get_policy_or_404(db, policy_id, current.tenant_id)
    rows = db.scalars(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.version_number.desc())
    ).all()
    return [PolicyVersionResponse.model_validate(r) for r in rows]


@router.post("/{policy_id}/rollback/{version_number}", response_model=PolicyResponse)
def rollback_policy(
    policy_id: UUID,
    version_number: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyResponse:
    """Roll back a policy to a previous version snapshot."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    policy = _get_policy_or_404(db, policy_id, current.tenant_id)
    snap = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.version_number == version_number,
        )
    )
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")

    old_value = dict(policy.value)
    policy.value = snap.value_snapshot
    policy.version = (policy.version or 0) + 1
    db.flush()

    _snapshot_version(db, policy, current.user_id, f"Rolled back to version {version_number}")
    _record_policy_audit(db, policy, "ROLLBACK", old_value, snap.value_snapshot, current.user_id)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


# ─── Policy approval workflow ─────────────────────────────────────────────────

@router.post("/{policy_id}/approvals", response_model=PolicyApprovalResponse, status_code=status.HTTP_201_CREATED)
def request_policy_approval(
    policy_id: UUID,
    payload: PolicyApprovalCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyApprovalResponse:
    """Request approval for a proposed policy value change."""
    _get_policy_or_404(db, policy_id, current.tenant_id)

    approval = PolicyApproval(
        tenant_id=current.tenant_id,
        policy_id=policy_id,
        requested_by_user_id=current.user_id,
        proposed_value=payload.proposed_value,
        status=PolicyApprovalStatus.PENDING,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return PolicyApprovalResponse.model_validate(approval)


@router.post("/{policy_id}/approvals/{approval_id}/approve", response_model=PolicyApprovalResponse)
def approve_policy(
    policy_id: UUID,
    approval_id: UUID,
    payload: PolicyApprovalReview,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyApprovalResponse:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    approval = _get_approval_or_404(db, approval_id, policy_id)
    if approval.status != PolicyApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Approval is no longer pending")
    if approval.requested_by_user_id == current.user_id:
        raise HTTPException(status_code=409, detail="Cannot self-approve: 2-person rule required")

    policy = _get_policy_or_404(db, policy_id, current.tenant_id)
    old_value = dict(policy.value)

    approval.status = PolicyApprovalStatus.APPROVED
    approval.reviewed_by_user_id = current.user_id
    approval.review_reason = payload.reason

    policy.value = approval.proposed_value
    policy.version = (policy.version or 0) + 1
    db.flush()

    _snapshot_version(db, policy, current.user_id, f"Approved via policy approval {approval_id}")
    _record_policy_audit(db, policy, "UPDATE", old_value, approval.proposed_value, current.user_id)
    db.commit()
    db.refresh(approval)
    return PolicyApprovalResponse.model_validate(approval)


@router.post("/{policy_id}/approvals/{approval_id}/deny", response_model=PolicyApprovalResponse)
def deny_policy(
    policy_id: UUID,
    approval_id: UUID,
    payload: PolicyApprovalReview,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> PolicyApprovalResponse:
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    approval = _get_approval_or_404(db, approval_id, policy_id)
    if approval.status != PolicyApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Approval is no longer pending")

    approval.status = PolicyApprovalStatus.DENIED
    approval.reviewed_by_user_id = current.user_id
    approval.review_reason = payload.reason
    db.commit()
    db.refresh(approval)
    return PolicyApprovalResponse.model_validate(approval)


@router.get("/{policy_id}/approvals", response_model=list[PolicyApprovalResponse])
def list_policy_approvals(
    policy_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[PolicyApprovalResponse]:
    _get_policy_or_404(db, policy_id, current.tenant_id)
    rows = db.scalars(
        select(PolicyApproval)
        .where(PolicyApproval.policy_id == policy_id)
        .order_by(PolicyApproval.created_at.desc())
    ).all()
    return [PolicyApprovalResponse.model_validate(r) for r in rows]


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_policy_or_404(db: Session, policy_id: UUID, tenant_id: UUID) -> TenantPolicy:
    policy = db.scalar(
        select(TenantPolicy).where(
            TenantPolicy.id == policy_id,
            TenantPolicy.tenant_id == tenant_id,
        )
    )
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


def _get_approval_or_404(db: Session, approval_id: UUID, policy_id: UUID) -> PolicyApproval:
    approval = db.scalar(
        select(PolicyApproval).where(
            PolicyApproval.id == approval_id,
            PolicyApproval.policy_id == policy_id,
        )
    )
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return approval


def _snapshot_version(db: Session, policy: TenantPolicy, changed_by: UUID, reason: str | None) -> None:
    snap = PolicyVersion(
        tenant_id=policy.tenant_id,
        policy_id=policy.id,
        version_number=policy.version,
        value_snapshot=dict(policy.value),
        changed_by_user_id=changed_by,
        change_reason=reason,
    )
    db.add(snap)
    db.flush()


def _record_policy_audit(
    db: Session,
    policy: TenantPolicy,
    change_type: str,
    old_value: dict | None,
    new_value: dict,
    changed_by: UUID,
) -> None:
    audit = PolicyChangeAuditEvent(
        tenant_id=policy.tenant_id,
        policy_id=policy.id,
        policy_key=policy.key,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=changed_by,
        created_at=datetime.now(UTC),
    )
    db.add(audit)
    db.flush()
