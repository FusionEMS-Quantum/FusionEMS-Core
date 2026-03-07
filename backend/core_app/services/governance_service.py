import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from core_app.models.governance import (
    AuthenticationEvent, AuthenticationEventType,
    UserSession, SupportAccessGrant, PhiaAccessAudit,
    ProtectedActionApproval, ProtectedActionStatus,
    DataExportRequest, TenantPolicy
)
from core_app.models.user import User
from core_app.core.errors import AppError

class GovernanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Authentication & Access Control ---

    def log_auth_event(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: AuthenticationEventType,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> AuthenticationEvent:
        event = AuthenticationEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata or {}
        )
        self.db.add(event)
        self.db.flush()
        return event

    def create_support_access(
        self,
        tenant_id: uuid.UUID,
        granted_to_user_id: uuid.UUID,
        reason: str,
        duration_minutes: int = 60
    ) -> SupportAccessGrant:
        grant = SupportAccessGrant(
            tenant_id=tenant_id,
            granted_to_user_id=granted_to_user_id,
            reason=reason,
            expires_at=datetime.now(UTC) + timedelta(minutes=duration_minutes)
        )
        self.db.add(grant)
        self.db.flush()
        return grant

    # --- PHI & Audit ---

    def audit_phi_access(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        access_type: str,
        fields: list[str],
        reason: str | None = None
    ) -> PhiaAccessAudit:
        audit = PhiaAccessAudit(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_type=access_type,
            fields_accessed=fields,
            reason=reason
        )
        self.db.add(audit)
        self.db.flush()
        return audit

    # --- Protected Actions ---

    def request_protected_action(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action_type: str,
        resource_id: uuid.UUID
    ) -> ProtectedActionApproval:
        approval = ProtectedActionApproval(
            tenant_id=tenant_id,
            requested_by_user_id=user_id,
            action_type=action_type,
            resource_id=resource_id,
            status=ProtectedActionStatus.PENDING
        )
        self.db.add(approval)
        self.db.flush()
        return approval

    def approve_protected_action(
        self,
        approval_id: uuid.UUID,
        approver_user_id: uuid.UUID,
        reason: str
    ) -> ProtectedActionApproval:
        approval = self.db.get(ProtectedActionApproval, approval_id)
        if not approval:
            raise AppError("GOVERNANCE_APPROVAL_NOT_FOUND", "Approval request not found", 404)
        
        approval.status = ProtectedActionStatus.APPROVED
        approval.approved_by_user_id = approver_user_id
        approval.reason = reason
        self.db.flush()
        return approval

    # --- Compliance Dashboard Queries ---

    def get_compliance_summary(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        # Failed Logins (last 24h)
        failed_logins = self.db.execute(
            select(AuthenticationEvent)
            .where(
                AuthenticationEvent.tenant_id == tenant_id,
                AuthenticationEvent.event_type == AuthenticationEventType.LOGIN_FAILED,
                AuthenticationEvent.created_at >= datetime.now(UTC) - timedelta(hours=24)
            )
        ).scalars().all()

        # Sensitive Access spikes (last 24h count)
        phi_spike = self.db.query(PhiaAccessAudit).filter(
            PhiaAccessAudit.tenant_id == tenant_id,
            PhiaAccessAudit.created_at >= datetime.now(UTC) - timedelta(hours=24)
        ).count()

        # Pending Approvals
        pending_approvals = self.db.query(ProtectedActionApproval).filter(
            ProtectedActionApproval.tenant_id == tenant_id,
            ProtectedActionApproval.status == ProtectedActionStatus.PENDING
        ).count()

        # Recent Exports
        recent_exports = self.db.query(DataExportRequest).filter(
            DataExportRequest.tenant_id == tenant_id,
            DataExportRequest.created_at >= datetime.now(UTC) - timedelta(days=7)
        ).count()

        return {
            "failed_logins_24h": len(failed_logins),
            "phi_access_count_24h": phi_spike,
            "pending_approvals_count": pending_approvals,
            "recent_exports_7d": recent_exports,
            "health_score": self._calculate_health_score(tenant_id),
            "status": "GREEN" if phi_spike < 100 and len(failed_logins) < 5 else "YELLOW"
        }

    def _calculate_health_score(self, tenant_id: uuid.UUID) -> int:
        # Simplified scoring logic
        score = 100
        # Deduct for failed logins
        failed_count = self.db.query(AuthenticationEvent).filter(
            AuthenticationEvent.tenant_id == tenant_id,
            AuthenticationEvent.event_type == AuthenticationEventType.LOGIN_FAILED,
            AuthenticationEvent.created_at >= datetime.now(UTC) - timedelta(hours=24)
        ).count()
        score -= min(failed_count * 5, 30)
        
        # Deduct for unapproved risky actions
        pending = self.db.query(ProtectedActionApproval).filter(
            ProtectedActionApproval.tenant_id == tenant_id,
            ProtectedActionApproval.status == ProtectedActionStatus.PENDING
        ).count()
        score -= min(pending * 10, 40)
        
        return max(score, 0)
