# pylint: disable=unsubscriptable-object
from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TaxFilingStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    TRANSMITTING = "TRANSMITTING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class IRSFilingForm(StrEnum):
    SCHEDULE_C = "1040_SCHEDULE_C"
    FORM_1120S = "1120_S"
    WISCONSIN_WT_4 = "WI_WT4"
    QUARTERLY_ESTIMATED = "1040_ES"
    FORM_1040_INDIVIDUAL = "1040_INDIVIDUAL"
    SCHEDULE_A_ITEMIZED = "1040_SCHEDULE_A"

class ExpensePaymentSource(StrEnum):
    BUSINESS_CHECKING = "BUSINESS_CHECKING"
    BUSINESS_CREDIT = "BUSINESS_CREDIT"
    PERSONAL_CREDIT_CARD = "PERSONAL_CREDIT_CARD_COMMINGLED"
    PERSONAL_CASH = "PERSONAL_CASH_OUT_OF_POCKET"

class TaxEntityBucket(StrEnum):
    BUSINESS = "BUSINESS_LLC"
    PERSONAL = "PERSONAL_INDIVIDUAL"
    FAMILY_DEPENDENT = "FAMILY_DEPENDENT"

class TaxDocumentType(StrEnum):
    RECEIPT = "RECEIPT"
    W2 = "W2"
    FORM_1099 = "1099"
    SCHEDULE_K1 = "K1"
    MEDICAL_HSA = "MEDICAL_HSA"
    BOARD_MINUTES = "BOARD_MINUTES"
    TAX_RETURN = "TAX_RETURN"
    IRS_CORRESPONDENCE = "IRS_NOTICE"

class TaxDocumentVault(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AWS S3 secure vault for receipts, W-2s, 1099s, and family tax documents.
    Strictly segregates personal vs business data with AWS KMS encryption.
    """
    __tablename__ = "tax_document_vault"

    tax_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bucket_classification: Mapped[TaxEntityBucket] = mapped_column(String(50), default=TaxEntityBucket.BUSINESS, index=True)
    document_type: Mapped[TaxDocumentType] = mapped_column(String(50), index=True)

    document_name: Mapped[str] = mapped_column(String(255))
    aws_s3_key: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    aws_bucket_name: Mapped[str] = mapped_column(String(255))

    # E.g., application/pdf, image/jpeg
    mime_type: Mapped[str] = mapped_column(String(100))
    is_encrypted_at_rest: Mapped[bool] = mapped_column(Boolean, default=True)

    # Document tags for AI retrieval (e.g. "2026", "W-2", "Wife", "Childcare")
    ai_tags: Mapped[list[str]] = mapped_column(JSON, default=list)


class QuantumTemporalLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable Append-Only Ledger. True Fortune-500 level accounting.
    Updates must be made via reversing/counter entries, never deletions.
    """
    __tablename__ = "quantum_temporal_ledger"

    entry_date: Mapped[date] = mapped_column(Date, index=True)
    debit_account: Mapped[str] = mapped_column(String(100), index=True) # e.g., "AWS_HOSTING_EXPENSE"
    credit_account: Mapped[str] = mapped_column(String(100), index=True) # e.g., "OWNER_CAPITAL_CONTRIBUTION"
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    description: Mapped[str] = mapped_column(String(500))
    is_reversing_entry: Mapped[bool] = mapped_column(Boolean, default=False)
    original_entry_id_if_reversed: Mapped[UUID | None] = mapped_column(ForeignKey("quantum_temporal_ledger.id"), nullable=True)

    # Cryptographic Audit Hash (Like an internal blockchain)
    audit_hash: Mapped[str] = mapped_column(String(255), nullable=True)


class FounderExpense(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Core ledger for business expenses, bypassing QuickBooks.
    AI categorizes everything against IRS standard deduction categories.
    """
    __tablename__ = "founder_expenses"

    merchant_name: Mapped[str] = mapped_column(String(255), index=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # AI Extracted Data
    irs_category: Mapped[str] = mapped_column(String(100))  # e.g., "Office Expense", "Utilities", "Meals"
    business_purpose: Mapped[str] = mapped_column(String(500))
    is_home_office_prorated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Section 195 Startup Cost Tracking (Crucial for pre-revenue phase)
    is_startup_expense_sec195: Mapped[bool] = mapped_column(Boolean, default=True)

    # Commingling / Out-of-Pocket Shield
    payment_source: Mapped[ExpensePaymentSource] = mapped_column(String(50), default=ExpensePaymentSource.BUSINESS_CREDIT)
    is_owner_capital_contribution: Mapped[bool] = mapped_column(Boolean, default=False)
    reimbursed_via_accountable_plan: Mapped[bool] = mapped_column(Boolean, default=False)

    # Android App Receipt Upload
    receipt_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ai_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    ai_raw_ocr_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    human_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class TaxFilingTransmission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Prepares the data for IRS Modernized e-File (MeF) and WI Dept of Revenue.
    """
    __tablename__ = "tax_filing_transmissions"

    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    form_type: Mapped[IRSFilingForm] = mapped_column(String(50))
    status: Mapped[TaxFilingStatus] = mapped_column(String(50), default=TaxFilingStatus.DRAFT)

    # The actual compiled JSON representation of the tax return
    compiled_tax_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Responses from the IRS MeF gateway
    irs_submission_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rejection_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Real-time Webhook E-file tracking (Intuit style real-time tracker)
    realtime_efile_status_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_irs_status_check_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class RealtimeTaxStrategy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks active 'Domination Level' tax loopholes and strategies identified by the AI.
    """
    __tablename__ = "realtime_tax_strategies"

    strategy_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1024))
    estimated_tax_savings: Mapped[float] = mapped_column(Float, default=0.0)

    bucket_target: Mapped[TaxEntityBucket] = mapped_column(String(50))
    is_implemented: Mapped[bool] = mapped_column(Boolean, default=False)
    implementation_steps_json: Mapped[dict] = mapped_column(JSON, default=dict)

