from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProtectedActionApprovalBase(BaseModel):
    action_type: str
    resource_id: UUID


class ProtectedActionApprovalCreate(ProtectedActionApprovalBase):
    pass


class ProtectedActionApprovalResponse(ProtectedActionApprovalBase):
    id: UUID
    tenant_id: UUID
    requested_by_user_id: UUID
    status: str
    approved_by_user_id: UUID | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceSummaryResponse(BaseModel):
    failed_logins_24h: int
    phi_access_count_24h: int
    pending_approvals_count: int
    recent_exports_7d: int
    health_score: int
    status: str


class PhiAccessAuditCreate(BaseModel):
    resource_type: str
    resource_id: UUID
    access_type: str
    fields: list[str]


class PhiAccessAuditResponse(PhiAccessAuditCreate):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportGrantCreate(BaseModel):
    granted_to_user_id: UUID
    reason: str
    duration_minutes: int = 60


class SupportGrantResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    granted_to_user_id: UUID
    reason: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
