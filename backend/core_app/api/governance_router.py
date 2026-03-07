from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.schemas.governance import (
    ComplianceSummaryResponse,
    PhiAccessAuditCreate,
    PhiAccessAuditResponse,
    ProtectedActionApprovalResponse,
    SupportGrantCreate,
    SupportGrantResponse,
)
from core_app.services.governance_service import GovernanceService
from core_app.models.governance import ProtectedActionStatus, ProtectedActionApproval

router = APIRouter(prefix="/governance", tags=["governance"])

@router.get("/summary", response_model=ComplianceSummaryResponse)
def get_compliance_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
) -> dict[str, Any]:
    """Founder Compliance Command Center Summary."""
    service = GovernanceService(db)
    # Only Founder/AgencyAdmin can see summary
    if current.role not in ["founder", "agency_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return service.get_compliance_summary(current.tenant_id)

@router.post("/phi-audit", response_model=PhiAccessAuditResponse)
def audit_phi_access(
    payload: PhiAccessAuditCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
):
    """Log PHI access for audit and traceability."""
    service = GovernanceService(db)
    return service.audit_phi_access(
        tenant_id=current.tenant_id,
        user_id=current.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        access_type=payload.access_type,
        fields=payload.fields
    )

@router.get("/approvals/pending", response_model=list[ProtectedActionApprovalResponse])
def list_pending_approvals(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
):
    """List all pending protected action approvals."""
    if current.role not in ["founder", "agency_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return db.query(ProtectedActionApproval).filter(
        ProtectedActionApproval.tenant_id == current.tenant_id,
        ProtectedActionApproval.status == ProtectedActionStatus.PENDING
    ).all()

@router.post("/approvals/{approval_id}/approve", response_model=ProtectedActionApprovalResponse)
def approve_action(
    approval_id: UUID,
    reason: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
):
    """Approve a protected action."""
    if current.role not in ["founder", "agency_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    service = GovernanceService(db)
    return service.approve_protected_action(approval_id, current.user_id, reason)

@router.post("/support-grant", response_model=SupportGrantResponse)
def grant_support_access(
    payload: SupportGrantCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency)
):
    """Grant temporary support access to an external or support user."""
    # Only Founder can grant support access
    if current.role != "founder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    service = GovernanceService(db)
    return service.create_support_access(
        current.tenant_id, payload.granted_to_user_id, payload.reason, payload.duration_minutes
    )
