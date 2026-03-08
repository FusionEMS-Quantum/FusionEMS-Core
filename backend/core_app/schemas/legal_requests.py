from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

RequestTypeLiteral = Literal["hipaa_roi", "subpoena", "court_order"]
RequestStatusLiteral = Literal[
    "received",
    "triage_complete",
    "missing_docs",
    "under_review",
    "packet_building",
    "delivered",
    "closed",
]
RequesterCategoryLiteral = Literal[
    "patient",
    "patient_representative",
    "attorney",
    "insurance",
    "government_agency",
    "employer",
    "other_third_party_manual_review",
]
LegalWorkflowStateLiteral = Literal[
    "request_received",
    "missing_information",
    "fee_calculated",
    "payment_required",
    "payment_link_created",
    "payment_completed",
    "ready_for_fulfillment_review",
    "ready_to_mail",
    "address_review_required",
    "cost_review_required",
    "manual_approval_required",
    "delivered",
    "refunded",
]
LegalPaymentStatusLiteral = Literal[
    "not_required",
    "payment_required",
    "payment_link_created",
    "payment_completed",
    "payment_failed",
    "check_expected",
    "check_received_by_agency",
    "check_deposit_pending",
    "check_cleared",
    "check_posted",
    "check_exception",
    "refunded",
]
MarginStatusLiteral = Literal[
    "profitable",
    "low_margin",
    "at_risk_of_loss",
    "manual_review_required",
]
RedactionModeLiteral = Literal[
    "court_safe_minimum_necessary",
    "expanded_disclosure_reviewed",
    "expanded_disclosure_patient_authorized",
    "expanded_disclosure_legal_override",
]


class MissingItemCard(BaseModel):
    code: str
    title: str
    detail: str
    severity: Literal["high", "medium", "low"]


class LegalTriageSummary(BaseModel):
    classification: RequestTypeLiteral
    classification_confidence: float = Field(ge=0.0, le=1.0)
    likely_invalid_or_incomplete: bool
    urgency_level: Literal["low", "normal", "high", "critical"]
    deadline_risk: Literal["none", "watch", "high"]
    mismatch_signals: list[str] = Field(default_factory=list)
    rationale: str


class RequiredDocumentChecklistItem(BaseModel):
    code: str
    label: str
    required: bool = True
    satisfied: bool = False


class LegalRequestIntakeIn(BaseModel):
    request_type: RequestTypeLiteral | None = None
    requesting_party: str = Field(min_length=2, max_length=255)
    requester_name: str = Field(min_length=2, max_length=255)
    requesting_entity: str | None = Field(default=None, max_length=255)
    requester_category: RequesterCategoryLiteral = "other_third_party_manual_review"

    patient_first_name: str | None = Field(default=None, max_length=128)
    patient_last_name: str | None = Field(default=None, max_length=128)
    patient_dob: date | None = None
    mrn: str | None = Field(default=None, max_length=128)
    csn: str | None = Field(default=None, max_length=128)

    date_range_start: date | None = None
    date_range_end: date | None = None

    request_documents: list[str] = Field(default_factory=list)
    requested_page_count: int = Field(default=0, ge=0, le=10000)
    jurisdiction_state: str = Field(default="WI", min_length=2, max_length=8)
    print_mail_requested: bool = False
    rush_requested: bool = False

    delivery_preference: Literal["secure_one_time_link", "encrypted_email", "manual_pickup"] = (
        "secure_one_time_link"
    )
    deadline_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("request_documents")
    @classmethod
    def _normalize_request_documents(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item and item.strip()]

    @field_validator("date_range_end")
    @classmethod
    def _validate_date_range(cls, value: date | None, info) -> date | None:
        start = info.data.get("date_range_start")
        if value and start and value < start:
            raise ValueError("date_range_end must be greater than or equal to date_range_start")
        return value


class LegalRequestIntakeOut(BaseModel):
    request_id: UUID
    intake_token: str
    status: RequestStatusLiteral
    request_type: RequestTypeLiteral
    triage_summary: LegalTriageSummary
    missing_items: list[MissingItemCard]
    required_document_checklist: list[RequiredDocumentChecklistItem]
    workflow_state: LegalWorkflowStateLiteral = "request_received"
    payment_status: LegalPaymentStatusLiteral = "not_required"
    payment_required: bool = False
    margin_status: MarginStatusLiteral = "manual_review_required"
    fee_quote: dict[str, object] = Field(default_factory=dict)


class LegalRequestClassifyIn(BaseModel):
    request_type: RequestTypeLiteral | None = None
    notes: str | None = None
    request_documents: list[str] = Field(default_factory=list)
    deadline_at: datetime | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None


class LegalRequestClassifyOut(BaseModel):
    triage_summary: LegalTriageSummary
    missing_items: list[MissingItemCard]
    required_document_checklist: list[RequiredDocumentChecklistItem]


class LegalUploadPresignIn(BaseModel):
    intake_token: str = Field(min_length=16)
    document_kind: str = Field(min_length=2, max_length=128)
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=128)


class LegalUploadPresignOut(BaseModel):
    upload_id: UUID
    upload_url: str
    key: str
    expires_in_seconds: int


class LegalUploadCompleteIn(BaseModel):
    intake_token: str = Field(min_length=16)
    upload_id: UUID
    byte_size: int = Field(ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=128)


class LegalUploadCompleteOut(BaseModel):
    request_id: UUID
    status: RequestStatusLiteral
    triage_summary: LegalTriageSummary
    missing_items: list[MissingItemCard]
    required_document_checklist: list[RequiredDocumentChecklistItem]


class LegalQueueItemOut(BaseModel):
    id: UUID
    request_type: RequestTypeLiteral
    status: RequestStatusLiteral
    requester_name: str
    requesting_party: str
    requesting_entity: str | None
    deadline_at: datetime | None
    deadline_risk: Literal["none", "watch", "high"]
    missing_count: int
    redaction_mode: RedactionModeLiteral
    workflow_state: LegalWorkflowStateLiteral = "request_received"
    payment_status: LegalPaymentStatusLiteral = "not_required"
    payment_required: bool = False
    margin_status: MarginStatusLiteral = "manual_review_required"
    created_at: datetime
    updated_at: datetime


class LegalPricingLineItem(BaseModel):
    code: str
    label: str
    amount_cents: int
    payee: Literal["agency", "platform", "vendor", "waived"]
    note: str | None = None


class LegalCostBreakdown(BaseModel):
    estimated_processor_fee_cents: int
    estimated_labor_cost_cents: int
    estimated_lob_cost_cents: int
    estimated_platform_margin_cents: int


class LegalFeeQuoteOut(BaseModel):
    request_id: UUID
    currency: str
    total_due_cents: int
    agency_payout_cents: int
    platform_fee_cents: int
    margin_status: MarginStatusLiteral
    payment_required: bool
    workflow_state: LegalWorkflowStateLiteral
    requester_category: RequesterCategoryLiteral
    delivery_mode: Literal["secure_digital", "print_and_mail", "manual_pickup"]
    line_items: list[LegalPricingLineItem]
    costs: LegalCostBreakdown
    hold_reasons: list[str] = Field(default_factory=list)


class LegalPricingQuoteIn(BaseModel):
    intake_token: str = Field(min_length=16)
    requested_page_count: int | None = Field(default=None, ge=0, le=10000)
    print_mail_requested: bool | None = None
    rush_requested: bool | None = None


class LegalPaymentCheckoutIn(BaseModel):
    intake_token: str = Field(min_length=16)
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class LegalPaymentCheckoutOut(BaseModel):
    request_id: UUID
    payment_id: UUID
    payment_status: LegalPaymentStatusLiteral
    workflow_state: LegalWorkflowStateLiteral
    checkout_url: str
    checkout_session_id: str
    connected_account_id: str
    amount_due_cents: int
    agency_payout_cents: int
    platform_fee_cents: int


class LegalRequestPaymentOut(BaseModel):
    payment_id: UUID
    request_id: UUID
    status: LegalPaymentStatusLiteral
    amount_due_cents: int
    amount_collected_cents: int
    platform_fee_cents: int
    agency_payout_cents: int
    currency: str
    stripe_connected_account_id: str | None
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
    check_reference: str | None
    paid_at: datetime | None
    failed_at: datetime | None
    refunded_at: datetime | None


class LegalCheckReceivedIn(BaseModel):
    check_reference: str = Field(min_length=2, max_length=128)


class LegalRequestsSummaryOut(BaseModel):
    total_open: int
    lane_counts: dict[str, int]
    urgent_deadlines: int
    high_risk_requests: int


class ChainOfCustodyTimelineEvent(BaseModel):
    event_type: str
    state: str
    created_at: datetime
    actor_user_id: UUID | None
    evidence: dict[str, object]


class AuditTimelineEvent(BaseModel):
    event_type: str
    created_at: datetime
    actor_user_id: UUID | None
    correlation_id: str | None
    payload: dict[str, object]


class LegalUploadOut(BaseModel):
    id: UUID
    document_kind: str
    file_name: str
    mime_type: str
    storage_uri: str
    byte_size: int
    checksum_sha256: str | None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LegalRequestDetailOut(BaseModel):
    id: UUID
    clinical_record_id: UUID
    request_type: RequestTypeLiteral
    status: RequestStatusLiteral
    requesting_party: str
    requester_name: str
    requesting_entity: str | None
    patient_first_name: str | None
    patient_last_name: str | None
    patient_dob: date | None
    mrn: str | None
    csn: str | None
    requested_date_from: date | None
    requested_date_to: date | None
    delivery_preference: str
    deadline_at: datetime | None
    triage_summary: LegalTriageSummary
    missing_items: list[MissingItemCard]
    required_document_checklist: list[RequiredDocumentChecklistItem]
    review_gate: dict[str, object]
    redaction_mode: RedactionModeLiteral
    requester_category: RequesterCategoryLiteral
    workflow_state: LegalWorkflowStateLiteral
    payment_status: LegalPaymentStatusLiteral
    payment_required: bool
    margin_status: MarginStatusLiteral
    delivery_mode: Literal["secure_digital", "print_and_mail", "manual_pickup"]
    fee_quote: dict[str, object]
    financial_snapshot: dict[str, object]
    fulfillment_gate: dict[str, object]
    review_notes: str | None
    packet_manifest: dict[str, object]
    uploads: list[LegalUploadOut]
    audit_timeline: list[AuditTimelineEvent]
    custody_timeline: list[ChainOfCustodyTimelineEvent]
    created_at: datetime
    updated_at: datetime


class LegalRequestReviewIn(BaseModel):
    authority_valid: bool
    identity_verified: bool
    completeness_valid: bool
    document_sufficient: bool
    minimum_necessary_scope: bool
    redaction_mode: RedactionModeLiteral = "court_safe_minimum_necessary"
    delivery_method: Literal["secure_one_time_link", "encrypted_email", "manual_pickup"]
    decision: Literal["approve", "request_more_docs", "reject"]
    decision_notes: str | None = Field(default=None, max_length=4000)


class LegalRequestReviewOut(BaseModel):
    request_id: UUID
    status: RequestStatusLiteral
    redaction_mode: RedactionModeLiteral
    review_gate: dict[str, object]
    workflow_state: LegalWorkflowStateLiteral = "request_received"
    payment_status: LegalPaymentStatusLiteral = "not_required"


class LegalPacketBuildOut(BaseModel):
    request_id: UUID
    status: RequestStatusLiteral
    packet_manifest: dict[str, object]


class DeliveryLinkCreateIn(BaseModel):
    expires_in_hours: int = Field(default=48, ge=1, le=168)
    recipient_hint: str | None = Field(default=None, max_length=255)


class DeliveryLinkOut(BaseModel):
    delivery_link_id: UUID
    delivery_url: str
    expires_at: datetime


class DeliveryAccessOut(BaseModel):
    request_id: UUID
    status: RequestStatusLiteral
    packet_manifest: dict[str, object]
    redaction_mode: RedactionModeLiteral


class LegalRequestCloseOut(BaseModel):
    request_id: UUID
    status: RequestStatusLiteral
