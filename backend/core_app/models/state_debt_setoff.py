from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StateDebtSetoffProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Platform-level configuration for a specific State's Debt Setoff Program.
    Enabled globally by platform admin, enrolled individually by agencies.
    """
    __tablename__ = "state_debt_setoff_profiles"

    state_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False) # e.g. "NC"
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Eligibility Rules
    min_debt_amount_cents: Mapped[int] = mapped_column(default=5000, nullable=False)
    min_days_delinquent: Mapped[int] = mapped_column(default=60, nullable=False)
    eligible_agency_types: Mapped[list[str]] = mapped_column(JSONB, default=["MUNICIPALITY", "COUNTY", "HOSPITAL_DISTRICT"], nullable=False)

    # Process
    export_format: Mapped[str] = mapped_column(String(64), default="CSV_STANDARD", nullable=False)
    submission_frequency: Mapped[str] = mapped_column(String(32), default="ANNUAL", nullable=False)

    active: Mapped[bool] = mapped_column(default=False, nullable=False)


class AgencyDebtSetoffEnrollment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks an agency's enrollment in the state program.
    """
    __tablename__ = "agency_debt_setoff_enrollments"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    state_profile_id: Mapped[UUID] = mapped_column(ForeignKey("state_debt_setoff_profiles.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # PENDING, ACTIVE, SUSPENDED
    enrollment_date: Mapped[datetime | None] = mapped_column(nullable=True)

    tax_id_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    agreement_signed: Mapped[bool] = mapped_column(default=False, nullable=False)


class DebtSetoffSubmissionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual debt item submitted to the state.
    """
    __tablename__ = "debt_setoff_submissions"

    enrollment_id: Mapped[UUID] = mapped_column(ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False) # Assuming patients table exists
    claim_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True) # Linked claim causing debt

    amount_submitted_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    submission_batch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", nullable=False) # SUBMITTED, REJECTED, ACCEPTED, PAID, REVERSED


class DebtSetoffResponseRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Response/Update from the state regarding a submission (e.g. Offset Success).
    """
    __tablename__ = "debt_setoff_responses"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_submissions.id"), nullable=False)

    response_code: Mapped[str] = mapped_column(String(64), nullable=True)
    amount_offset_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)


class DebtSetoffRulePack(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Per-state rule pack defining legal and procedural requirements for debt-setoff.
    Directive name: DebtSetoffRulePack
    """
    __tablename__ = "state_debt_setoff_rule_packs"

    state_profile_id: Mapped[UUID] = mapped_column(ForeignKey("state_debt_setoff_profiles.id"), unique=True, nullable=False)

    notice_required_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_offset_pct: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # % of refund that can be offset
    hardship_exemption_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    appeal_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    eligible_refund_types: Mapped[list[str]] = mapped_column(JSONB, default=["income_tax"], nullable=False)
    submission_format: Mapped[str] = mapped_column(String(64), default="CSV_STANDARD", nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSONB, default=["ssn", "full_name", "debt_amount", "account_number"], nullable=False)
    statute_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DebtSetoffExportBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks a batch submission of debts to a state debt-setoff program.
    Directive name: DebtSetoffExportBatch
    """
    __tablename__ = "debt_setoff_batches"

    enrollment_id: Mapped[UUID] = mapped_column(ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    batch_reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING, SUBMITTED, ACCEPTED, PARTIALLY_ACCEPTED, REJECTED
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    response_received_at: Mapped[datetime | None] = mapped_column(nullable=True)

    export_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # S3 key for exported CSV
    response_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)


class DebtSetoffNoticeRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks legally required notices sent to debtors before setoff submission.
    Each state requires a notice period (e.g., 30 days) before offset.
    """
    __tablename__ = "debt_setoff_notice_records"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_submissions.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    notice_type: Mapped[str] = mapped_column(String(32), nullable=False)  # INITIAL, FINAL, HEARING_SCHEDULED
    sent_via: Mapped[str] = mapped_column(String(16), nullable=False)  # MAIL, EMAIL, SMS
    sent_at: Mapped[datetime] = mapped_column(nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False)  # SENT, DELIVERED, RETURNED, FAILED
    required_response_by: Mapped[datetime | None] = mapped_column(nullable=True)
    response_received: Mapped[bool] = mapped_column(default=False, nullable=False)
    dispute_filed: Mapped[bool] = mapped_column(default=False, nullable=False)
    lob_tracking_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class DebtSetoffEligibilityDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Records the eligibility determination for individual debts.
    Enforces state-specific rules before submission.
    """
    __tablename__ = "debt_setoff_eligibility_decisions"

    enrollment_id: Mapped[UUID] = mapped_column(ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    claim_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    eligible: Mapped[bool] = mapped_column(default=False, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)  # ELIGIBLE, BELOW_THRESHOLD, AGING_INSUFFICIENT, PAYMENT_PLAN_ACTIVE, etc.
    debt_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    debt_aging_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_pack_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(nullable=False)
    override_by_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DebtSetoffRecoveryRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks successful recovery of funds through the debt setoff program.
    Created when money is received from the state offset.
    """
    __tablename__ = "debt_setoff_recovery_records"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_submissions.id"), nullable=False, index=True)
    response_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_responses.id"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    amount_recovered_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    recovery_date: Mapped[datetime] = mapped_column(nullable=False)
    applied_to_claim_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    applied_to_patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    ledger_entry_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK to patient_balance_ledger
    reconciled: Mapped[bool] = mapped_column(default=False, nullable=False)


class DebtSetoffReversalRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks reversals of debt setoff — when an offset is reversed due to
    dispute, hardship, or state-initiated correction.
    """
    __tablename__ = "debt_setoff_reversal_records"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_submissions.id"), nullable=False, index=True)
    recovery_id: Mapped[UUID | None] = mapped_column(ForeignKey("debt_setoff_recovery_records.id"), nullable=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    reversal_reason: Mapped[str] = mapped_column(String(64), nullable=False)  # DISPUTE_UPHELD, HARDSHIP_EXEMPTION, STATE_CORRECTION, DUPLICATE
    amount_reversed_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reversed_at: Mapped[datetime] = mapped_column(nullable=False)
    state_reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ledger_adjustment_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
