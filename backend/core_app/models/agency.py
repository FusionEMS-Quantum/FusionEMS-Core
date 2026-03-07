from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AgencyBillingPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Defines how an agency handles patient billing.
    See PART 5: AGENCY POLICY CONTROL in ZERO_ERROR_DIRECTIVE.md.
    """
    __tablename__ = "agency_billing_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    
    # Policy Toggles
    patient_billing_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    patient_self_pay_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    internal_follow_up_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    third_party_collections_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    payment_plans_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    state_debt_setoff_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Policy Details
    min_balance_for_statement: Mapped[int] = mapped_column(default=500, nullable=False)  # 5.00
    days_until_collections: Mapped[int] = mapped_column(default=120, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(default=30, nullable=False)


class AgencyCollectionsPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Specific rules for collections if enabled.
    """
    __tablename__ = "agency_collections_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    
    min_debt_amount_cents: Mapped[int] = mapped_column(default=5000, nullable=False) # $50
    vendor_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    auto_escalate: Mapped[bool] = mapped_column(default=False, nullable=False)


class AgencyPaymentPlanPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configures payment-plan rules per agency.
    """
    __tablename__ = "agency_payment_plan_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)

    max_installments: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    min_installment_cents: Mapped[int] = mapped_column(Integer, default=2500, nullable=False)  # $25
    interest_rate_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # basis points
    auto_enroll_threshold_cents: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)  # $100
    allow_custom_schedules: Mapped[bool] = mapped_column(default=False, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)


class AgencyWriteoffPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Rules governing when and how write-offs are authorized.
    """
    __tablename__ = "agency_writeoff_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)

    auto_writeoff_threshold_cents: Mapped[int] = mapped_column(Integer, default=500, nullable=False)  # $5
    max_auto_writeoff_cents: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)  # $50
    require_human_approval_above_cents: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    writeoff_aging_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    bad_debt_category: Mapped[str] = mapped_column(String(64), default="UNCOLLECTIBLE", nullable=False)


class AgencyDebtSetoffPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Agency-level configuration for state debt-setoff participation.
    """
    __tablename__ = "agency_debt_setoff_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)

    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    min_debt_cents: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)  # $50
    min_aging_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    exclude_payment_plan_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    exclude_appeal_in_progress: Mapped[bool] = mapped_column(default=True, nullable=False)
    max_submissions_per_batch: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    require_human_review: Mapped[bool] = mapped_column(default=True, nullable=False)


class AgencyPublicSectorProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tax and legal identity for public agencies.
    """
    __tablename__ = "agency_public_sector_profiles"
    
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    
    tax_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_municipality: Mapped[bool] = mapped_column(default=False, nullable=False)
    state_entity_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
