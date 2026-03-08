from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class LegalRequestType(enum.StrEnum):
    HIPAA_ROI = "hipaa_roi"
    SUBPOENA = "subpoena"
    COURT_ORDER = "court_order"


class LegalRequestStatus(enum.StrEnum):
    RECEIVED = "received"
    TRIAGE_COMPLETE = "triage_complete"
    MISSING_DOCS = "missing_docs"
    UNDER_REVIEW = "under_review"
    PACKET_BUILDING = "packet_building"
    DELIVERED = "delivered"
    CLOSED = "closed"


class RedactionMode(enum.StrEnum):
    COURT_SAFE_MINIMUM_NECESSARY = "court_safe_minimum_necessary"
    EXPANDED_DISCLOSURE_REVIEWED = "expanded_disclosure_reviewed"
    EXPANDED_DISCLOSURE_PATIENT_AUTHORIZED = "expanded_disclosure_patient_authorized"
    EXPANDED_DISCLOSURE_LEGAL_OVERRIDE = "expanded_disclosure_legal_override"


class DeliveryPreference(enum.StrEnum):
    SECURE_ONE_TIME_LINK = "secure_one_time_link"
    ENCRYPTED_EMAIL = "encrypted_email"
    MANUAL_PICKUP = "manual_pickup"


class RequesterCategory(enum.StrEnum):
    PATIENT = "patient"
    PATIENT_REPRESENTATIVE = "patient_representative"
    ATTORNEY = "attorney"
    INSURANCE = "insurance"
    GOVERNMENT_AGENCY = "government_agency"
    EMPLOYER = "employer"
    OTHER_THIRD_PARTY_MANUAL_REVIEW = "other_third_party_manual_review"


class LegalWorkflowState(enum.StrEnum):
    REQUEST_RECEIVED = "request_received"
    MISSING_INFORMATION = "missing_information"
    FEE_CALCULATED = "fee_calculated"
    PAYMENT_REQUIRED = "payment_required"
    PAYMENT_LINK_CREATED = "payment_link_created"
    PAYMENT_COMPLETED = "payment_completed"
    READY_FOR_FULFILLMENT_REVIEW = "ready_for_fulfillment_review"
    READY_TO_MAIL = "ready_to_mail"
    ADDRESS_REVIEW_REQUIRED = "address_review_required"
    COST_REVIEW_REQUIRED = "cost_review_required"
    MANUAL_APPROVAL_REQUIRED = "manual_approval_required"
    DELIVERED = "delivered"
    REFUNDED = "refunded"


class LegalPaymentStatus(enum.StrEnum):
    NOT_REQUIRED = "not_required"
    PAYMENT_REQUIRED = "payment_required"
    PAYMENT_LINK_CREATED = "payment_link_created"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    CHECK_EXPECTED = "check_expected"
    CHECK_RECEIVED_BY_AGENCY = "check_received_by_agency"
    CHECK_DEPOSIT_PENDING = "check_deposit_pending"
    CHECK_CLEARED = "check_cleared"
    CHECK_POSTED = "check_posted"
    CHECK_EXCEPTION = "check_exception"
    REFUNDED = "refunded"


class MarginRiskStatus(enum.StrEnum):
    PROFITABLE = "profitable"
    LOW_MARGIN = "low_margin"
    AT_RISK_OF_LOSS = "at_risk_of_loss"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class LegalRequestCommand(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "legal_request_commands"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True
    )
    request_type: Mapped[LegalRequestType] = mapped_column(
        Enum(LegalRequestType), nullable=False, index=True
    )
    status: Mapped[LegalRequestStatus] = mapped_column(
        Enum(LegalRequestStatus), nullable=False, default=LegalRequestStatus.RECEIVED, index=True
    )

    requesting_party: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requesting_entity: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patient_first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    patient_last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    patient_dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    mrn: Mapped[str | None] = mapped_column(String(128), nullable=True)
    csn: Mapped[str | None] = mapped_column(String(128), nullable=True)

    requested_date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    requested_date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivery_preference: Mapped[DeliveryPreference] = mapped_column(
        Enum(DeliveryPreference),
        nullable=False,
        default=DeliveryPreference.SECURE_ONE_TIME_LINK,
    )

    triage_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    missing_items: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    required_document_checklist: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    review_gate: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    redaction_mode: Mapped[RedactionMode] = mapped_column(
        Enum(RedactionMode),
        nullable=False,
        default=RedactionMode.COURT_SAFE_MINIMUM_NECESSARY,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    packet_manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    packet_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    intake_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requester_category: Mapped[str] = mapped_column(
        String(64), nullable=False, default=RequesterCategory.OTHER_THIRD_PARTY_MANUAL_REVIEW.value, index=True
    )
    workflow_state: Mapped[str] = mapped_column(
        String(64), nullable=False, default=LegalWorkflowState.REQUEST_RECEIVED.value, index=True
    )
    payment_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=LegalPaymentStatus.NOT_REQUIRED.value, index=True
    )
    payment_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    margin_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=MarginRiskStatus.MANUAL_REVIEW_REQUIRED.value, index=True
    )
    delivery_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="secure_digital")
    print_mail_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    rush_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    estimated_page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jurisdiction_state: Mapped[str] = mapped_column(String(8), nullable=False, default="WI")
    fee_quote: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    financial_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    fulfillment_gate: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class LegalRequestUpload(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "legal_request_uploads"

    legal_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_request_commands.id"), nullable=False, index=True
    )
    document_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    metadata_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class LegalDeliveryLink(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "legal_delivery_links"

    legal_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_request_commands.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recipient_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    download_ip: Mapped[str | None] = mapped_column(String(128), nullable=True)
    download_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)


class LegalRequestPayment(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "legal_request_payments"

    legal_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_request_commands.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="stripe")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default=LegalPaymentStatus.PAYMENT_REQUIRED.value)
    amount_due_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount_collected_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    platform_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agency_payout_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="usd")
    stripe_connected_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    check_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    check_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
