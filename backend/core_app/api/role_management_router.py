"""
Role management router — UserRoleAssignment CRUD with full audit trail.
Allows founders and agency admins to assign, revoke and list user roles.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.governance import (
    AuthorizationAuditEvent,
    Role,
)
from core_app.models.platform_core import UserRoleAssignment
from core_app.models.user import User
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/roles", tags=["roles"])

_ADMIN_ROLES = frozenset({"founder", "agency_admin"})


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRoleAssignmentCreate(BaseModel):
    user_id: UUID
    role_id: UUID


class UserRoleAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    role_name: str
    assigned_by_user_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Role catalogue ───────────────────────────────────────────────────────────

@router.get("", response_model=list[RoleResponse])
def list_roles(
    current: CurrentUser = Depends(get_current_user),  # auth gate — tenant must be authenticated
    db: Session = Depends(db_session_dependency),
) -> list[RoleResponse]:
    """List all system roles available for assignment."""
    _ = current  # auth gate: request must be authenticated
    rows = db.scalars(select(Role).order_by(Role.name)).all()
    return [RoleResponse.model_validate(r) for r in rows]


# ─── User role assignments ────────────────────────────────────────────────────

@router.get("/assignments", response_model=list[UserRoleAssignmentResponse])
def list_assignments(
    user_id: UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[UserRoleAssignmentResponse]:
    """List active role assignments for the current tenant (optionally filter by user)."""
    stmt = select(UserRoleAssignment).where(
        UserRoleAssignment.tenant_id == current.tenant_id,
        UserRoleAssignment.is_active == True,  # noqa: E712
    )
    if user_id is not None:
        stmt = stmt.where(UserRoleAssignment.user_id == user_id)
    rows = db.scalars(stmt).all()
    return [UserRoleAssignmentResponse.model_validate(r) for r in rows]


@router.post("/assignments", response_model=UserRoleAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_role(
    payload: UserRoleAssignmentCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> UserRoleAssignmentResponse:
    """Assign a role to a user within the current tenant."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges to assign roles")

    # Verify target user belongs to this tenant
    target_user = db.scalar(
        select(User).where(User.id == payload.user_id, User.tenant_id == current.tenant_id, User.deleted_at.is_(None))
    )
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Verify role exists
    role = db.scalar(select(Role).where(Role.id == payload.role_id))
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check for duplicate active assignment
    existing = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.tenant_id == current.tenant_id,
            UserRoleAssignment.user_id == payload.user_id,
            UserRoleAssignment.role_name == role.name,
            UserRoleAssignment.is_active == True,  # noqa: E712
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Role already assigned to this user")

    assignment = UserRoleAssignment(
        tenant_id=current.tenant_id,
        user_id=payload.user_id,
        role_name=role.name,
        assigned_by_user_id=current.user_id,
        is_active=True,
    )
    db.add(assignment)
    db.flush()

    _record_authz_audit(db, current, "assign_role", "user_role_assignment", assignment.id, "ALLOW")
    db.commit()
    db.refresh(assignment)
    return UserRoleAssignmentResponse.model_validate(assignment)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_role(
    assignment_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> None:
    """Revoke a role assignment. The audit trail is preserved — the record is not deleted."""
    if current.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient privileges to revoke roles")

    assignment = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.id == assignment_id,
            UserRoleAssignment.tenant_id == current.tenant_id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    if not assignment.is_active:
        raise HTTPException(status_code=409, detail="Role assignment is already revoked")

    assignment.is_active = False
    db.flush()

    _record_authz_audit(db, current, "revoke_role", "user_role_assignment", assignment_id, "ALLOW")
    db.commit()


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _record_authz_audit(
    db: Session,
    current: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: UUID,
    decision: str,
) -> None:
    event = AuthorizationAuditEvent(
        tenant_id=current.tenant_id,
        user_id=current.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
    )
    db.add(event)
    db.flush()
