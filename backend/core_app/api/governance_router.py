from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.governance import (
    ExternalIdentifier,
    HandoffExchangeRecord,
    InteropImportRecord,
    InteropPayload,
    ProtectedActionApproval,
    ProtectedActionStatus,
)
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


@router.get("/interop-readiness")
def get_interop_readiness_score(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Compute an interoperability readiness score (0–100) for the tenant.

    Scoring algorithm (25 pts each):
      1. External identifiers registered  (≥ 1 system mapped = 25pts)
      2. Handoff exchange records exist    (≥ 1 record = 25pts)
      3. Import records present            (≥ 1 import = 25pts)
      4. Inbound payloads received/validated (≥ 1 validated payload = 25pts)
    """
    if current.role not in ("founder", "agency_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    tid = current.tenant_id

    ext_count: int = db.scalar(
        select(func.count()).select_from(ExternalIdentifier).where(ExternalIdentifier.tenant_id == tid)  # pylint: disable=not-callable
    ) or 0
    handoff_count: int = db.scalar(
        select(func.count()).select_from(HandoffExchangeRecord).where(HandoffExchangeRecord.tenant_id == tid)  # pylint: disable=not-callable
    ) or 0
    import_count: int = db.scalar(
        select(func.count()).select_from(InteropImportRecord).where(InteropImportRecord.tenant_id == tid)  # pylint: disable=not-callable
    ) or 0
    validated_payload_count: int = db.scalar(
        select(func.count()).select_from(InteropPayload).where(  # pylint: disable=not-callable
            InteropPayload.tenant_id == tid,
            InteropPayload.status.in_(["validated", "transformed", "imported"]),
        )
    ) or 0

    breakdown = {
        "external_identifiers_mapped": ext_count,
        "handoff_records": handoff_count,
        "import_records": import_count,
        "validated_payloads": validated_payload_count,
    }

    score = (
        (25 if ext_count >= 1 else 0)
        + (25 if handoff_count >= 1 else 0)
        + (25 if import_count >= 1 else 0)
        + (25 if validated_payload_count >= 1 else 0)
    )

    if score >= 80:
        interop_status = "GREEN"
    elif score >= 50:
        interop_status = "YELLOW"
    else:
        interop_status = "RED"

    return {"score": score, "status": interop_status, "breakdown": breakdown}
