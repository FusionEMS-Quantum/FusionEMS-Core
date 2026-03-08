from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TenantBillingMode(StrEnum):
    FUSION_RCM = "fusionems_rcm"
    THIRD_PARTY = "third_party_internal"


class OperationalMode(StrEnum):
    HEMS_TRANSPORT = "hems_transport"
    EMS_TRANSPORT = "ems_transport"
    MEDICAL_TRANSPORT = "medical_transport"
    EXTERNAL_911_CAD = "external_911_cad"


class VoiceSessionState(StrEnum):
    CALL_RECEIVED = "call_received"
    LOOKUP_PENDING = "lookup_pending"
    LOOKUP_RESOLVED = "lookup_resolved"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    AI_HANDLING = "ai_handling"
    ACTION_PENDING = "action_pending"
    ACTION_COMPLETED = "action_completed"
    HUMAN_HANDOFF_REQUIRED = "human_handoff_required"
    HUMAN_CONNECTED = "human_connected"
    CALL_CLOSED = "call_closed"
    CALL_FAILED = "call_failed"


class BillingPhonePolicy(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID
    billing_mode: TenantBillingMode
    allow_ai_payment_plans: bool = False
    allow_ai_balance_waive: bool = False
    collections_enabled: bool = False
    escalation_priority: str = "normal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        orm_mode = True

class BillingVoiceSession(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: str # External session ID
    call_control_id: str # Telnyx ID
    caller_phone_number: str
    state: VoiceSessionState = VoiceSessionState.CALL_RECEIVED
    tenant_id: uuid.UUID | None = None
    statement_id: str | None = None
    patient_account_id: str | None = None
    ai_intent: str | None = None
    transcript_summary: str | None = None
    escalation_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        orm_mode = True
