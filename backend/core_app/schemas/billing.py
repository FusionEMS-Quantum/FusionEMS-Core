"""
Centralized Billing Pydantic Schemas
======================================
All billing-domain request/response models live here.
Router files import from this module — no ad-hoc inline models.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Claim Schemas ─────────────────────────────────────────────────────────────

class ClaimSummary(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    patient_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    patient_balance_status: str
    total_billed_cents: int
    insurance_paid_cents: int
    patient_responsibility_cents: int
    patient_paid_cents: int
    remaining_collectible_balance_cents: int
    aging_days: int
    primary_payer_name: str | None = None
    is_valid: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimIssueOut(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    severity: str
    source: str
    what_is_wrong: str
    why_it_matters: str
    what_to_do_next: str
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimAuditEventOut(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    user_id: uuid.UUID | None = None
    event_type: str
    old_value: str | None = None
    new_value: str | None = None
    metadata_blob: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Pre-Submission Rules ──────────────────────────────────────────────────────

class PreSubmissionRequest(BaseModel):
    claim_id: uuid.UUID


class RuleResultOut(BaseModel):
    rule_id: str
    severity: str
    passed: bool
    what_is_wrong: str = ""
    why_it_matters: str = ""
    what_to_do_next: str = ""


class PreSubmissionVerdictOut(BaseModel):
    claim_id: uuid.UUID
    submittable: bool
    results: list[RuleResultOut]
    blocking_count: int
    warning_count: int
    checked_at: str


# ── Billing AI Schemas ────────────────────────────────────────────────────────

class DenialPredictionRequest(BaseModel):
    claim_id: uuid.UUID
    payer_id: str = ""
    procedure_codes: list[str] = Field(default_factory=list)
    diagnosis_codes: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)


class DenialPredictionOut(BaseModel):
    claim_id: uuid.UUID
    risk_score: float
    risk_level: str
    top_risk_factors: list[str]
    recommended_actions: list[str]
    confidence: float
    model_version: str


class AppealStrategyRequest(BaseModel):
    claim_id: uuid.UUID
    denial_code: str


class AppealStrategyOut(BaseModel):
    claim_id: uuid.UUID
    denial_code: str
    recommended_strategy: str
    supporting_evidence: list[str]
    estimated_success_pct: float
    confidence: float
    model_version: str


class BillingHealthScoreOut(BaseModel):
    tenant_id: uuid.UUID
    overall_score: int
    grade: str
    factors: list[dict[str, Any]]
    recommendations: list[str]
    computed_at: str


# ── Payment / Stripe Schemas ─────────────────────────────────────────────────

class PaymentLinkRequest(BaseModel):
    account_id: uuid.UUID
    amount_cents: int
    patient_phone: str
    success_url: str
    cancel_url: str


class PaymentLinkEventOut(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    stripe_payment_link_id: str
    status: str
    sent_via: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Office Ally / EDI Schemas ─────────────────────────────────────────────────

class SubmitOfficeAllyRequest(BaseModel):
    submitter_id: str = Field(..., description="X12 ISA/GS sender id")
    receiver_id: str = Field(..., description="X12 receiver id")
    billing_npi: str
    billing_tax_id: str
    service_lines: list[dict[str, Any]] = Field(default_factory=list)


class EraImportRequest(BaseModel):
    x12_base64: str


# ── AR Aging ──────────────────────────────────────────────────────────────────

class ArAgingBucketOut(BaseModel):
    label: str
    count: int
    total_cents: int


class ArAgingReportOut(BaseModel):
    as_of_date: str
    total_ar_cents: int
    total_claims: int
    avg_days_in_ar: float
    buckets: list[ArAgingBucketOut]
    payer_breakdown: dict[str, Any]


# ── SaaS Pricing Schemas ─────────────────────────────────────────────────────

class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    stripe_product_id: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class PriceOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    amount_cents: int
    currency: str
    interval: str
    per_unit_amount_cents: int | None = None
    usage_type: str
    stripe_price_id: str | None = None
    active: bool
    version: int
    effective_from: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageMeterOut(BaseModel):
    id: uuid.UUID
    subscription_item_id: uuid.UUID
    tenant_id: uuid.UUID
    metric_name: str
    period_start: datetime
    period_end: datetime
    quantity: int
    reported_to_stripe: bool

    model_config = ConfigDict(from_attributes=True)


class BillingInvoiceMirrorOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    stripe_invoice_id: str
    status: str
    amount_due_cents: int
    amount_paid_cents: int
    currency: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    paid_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Agency Policy Schemas ─────────────────────────────────────────────────────

class AgencyBillingPolicyOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_billing_enabled: bool
    patient_self_pay_allowed: bool
    internal_follow_up_only: bool
    third_party_collections_enabled: bool
    payment_plans_allowed: bool
    state_debt_setoff_enabled: bool
    min_balance_for_statement: int
    days_until_collections: int
    grace_period_days: int

    model_config = ConfigDict(from_attributes=True)


class AgencyPaymentPlanPolicyOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    max_installments: int
    min_installment_cents: int
    interest_rate_bps: int
    auto_enroll_threshold_cents: int
    allow_custom_schedules: bool
    grace_period_days: int

    model_config = ConfigDict(from_attributes=True)


class AgencyWriteoffPolicyOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    auto_writeoff_threshold_cents: int
    max_auto_writeoff_cents: int
    require_human_approval_above_cents: int
    writeoff_aging_days: int
    bad_debt_category: str

    model_config = ConfigDict(from_attributes=True)


class AgencyDebtSetoffPolicyOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    enabled: bool
    min_debt_cents: int
    min_aging_days: int
    exclude_payment_plan_active: bool
    exclude_appeal_in_progress: bool
    max_submissions_per_batch: int
    require_human_review: bool

    model_config = ConfigDict(from_attributes=True)


# ── Debt Setoff Schemas ───────────────────────────────────────────────────────

class DebtSetoffExportBatchOut(BaseModel):
    id: uuid.UUID
    enrollment_id: uuid.UUID
    tenant_id: uuid.UUID
    batch_reference: str
    record_count: int
    total_amount_cents: int
    status: str
    submitted_at: datetime | None = None
    response_received_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DebtSetoffRulePackOut(BaseModel):
    id: uuid.UUID
    state_profile_id: uuid.UUID
    notice_required_days: int
    max_offset_pct: int
    hardship_exemption_enabled: bool
    appeal_window_days: int
    eligible_refund_types: list[str]
    submission_format: str
    required_fields: list[str]
    statute_reference: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Batch Resubmit / Command Center ──────────────────────────────────────────

class BatchResubmitRequest(BaseModel):
    claim_ids: list[uuid.UUID]
    resubmit_reason: str = "initial_denial"


class ContractSimRequest(BaseModel):
    payer_id: str
    proposed_rate_cents: int
    current_rate_cents: int
    annual_volume: int


class BillingAlertThresholdRequest(BaseModel):
    metric: str
    threshold_value: float
    alert_type: str = "email"
    recipients: list[str] = Field(default_factory=list)


class AppealDraftRequest(BaseModel):
    claim_id: uuid.UUID
    denial_reason: str
    supporting_context: str = ""


class PayerFollowUpRequest(BaseModel):
    payer_id: str
    claim_ids: list[uuid.UUID]
    follow_up_method: str = "phone"
