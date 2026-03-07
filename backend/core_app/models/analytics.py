from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AlertSeverity(StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

class AlertSource(StrEnum):
    METRIC_RUN = "METRIC_RUN"
    AI_REVIEW = "AI_REVIEW"
    BILLING_EVENT = "BILLING_EVENT"
    CLINICAL_EVENT = "CLINICAL_EVENT"
    OPS_EVENT = "OPS_EVENT"
    READINESS_EVENT = "READINESS_EVENT"
    HUMAN_NOTE = "HUMAN_NOTE"


# PART 3: EXECUTIVE KPI BUILD
class KPIComputationRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    run_time: datetime = Field(default_factory=datetime.utcnow)
    status: str
    error_message: str | None = None
    computation_time_ms: int | None = None

class KPIValueSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    run_id: UUID = Field(foreign_key="kpicomputationrun.id")
    metric_name: str
    metric_value: float
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)

class KPITrendPoint(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    metric_name: str
    trend_value: float
    trend_date: datetime

class HealthScoreFactor(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    score_name: str  # e.g., "Revenue Health Score"
    factor_name: str
    impact_value: float
    description: str

class ExecutiveAlert(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    title: str
    severity: AlertSeverity
    source: AlertSource
    what_changed: str
    why_it_matters: str
    what_you_should_do: str
    executive_context: str
    human_review: str
    confidence: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None

class ExecutiveSummarySnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    summary_ai_text: str
    revenue_score: float
    ops_score: float
    clinical_score: float
    workforce_score: float
    compliance_score: float


# PART 4: OPERATIONAL ANALYTICS BUILD
class OperationalMetricSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    request_volume: int
    escalation_rate: float
    failed_deliveries: int

class ResponseTimeMetric(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    average_response_ms: int

class QueuePerformanceMetric(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    average_time_in_queue_ms: int
    period_start: datetime
    period_end: datetime

class MissionTimingAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    average_mission_completion_ms: int
    period_start: datetime
    period_end: datetime

class PagingPerformanceAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    average_page_ack_time_ms: int
    period_start: datetime
    period_end: datetime

class TelemetryUptimeAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    uptime_percent: float
    period_start: datetime
    period_end: datetime


# PART 5: FINANCIAL / RCM ANALYTICS BUILD
class FinancialMetricSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    total_billed: float
    total_paid: float
    unresolved_remainder: float
    patient_balance_exposure: float
    payer_mix_json: str
    denial_rate: float
    rejection_rate: float
    autopay_failure_rate: float

class ARAgingBucket(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    bucket_name: str # e.g. "0-30", "31-60", "61-90", "90+"
    amount_usd: float

class DenialTrendAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    denial_reason_code: str
    count: int
    amount_usd: float

class PaymentLagAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    average_payment_lag_days: float

class SubscriptionRevenueAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    total_mrr: float

class CashAtRiskSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    at_risk_amount_usd: float
    risk_factors_json: str


# PART 6: CLINICAL / QA ANALYTICS BUILD
class ClinicalMetricSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    charts_waiting_sync: int
    charts_blocked_lock: int
    contradiction_flags: int
    missing_signature_rate: float

class QAQueueAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    qa_backlog_count: int
    correction_rate: float

class ValidationFailureAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    failure_category: str
    count: int

class SyncFailureAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    handoff_failure_rate: float

class NemsisExportAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    export_failure_rate: float

class ClinicalRiskTrendPoint(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    trend_date: datetime
    billing_risk_from_charting_count: int


# PART 7: WORKFORCE / READINESS ANALYTICS BUILD
class ReadinessMetricSnapshot(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    open_shifts_count: int
    understaffed_units_count: int
    fatigue_warnings_count: int
    out_of_service_count: int
    pm_overdue_count: int

class CoverageGapAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    coverage_gap_hours: float

class CredentialRiskAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    expiring_soon_count: int
    expired_count: int

class InventoryRiskAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    low_stock_count: int
    expiring_meds_count: int

class FleetReadinessAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    fleet_downtime_rate: float

class NarcoticsRiskAggregate(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    period_start: datetime
    period_end: datetime
    discrepancy_count: int


# PART 8: REPORTING / EXPORT BUILD
class ReportDefinition(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    name: str # e.g. "Founder Daily Summary"
    schedule_cron: str | None = None
    configuration_json: str

class ReportRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    report_definition_id: UUID = Field(foreign_key="reportdefinition.id")
    run_time: datetime = Field(default_factory=datetime.utcnow)
    status: str
    error_message: str | None = None

class ReportDelivery(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_run_id: UUID = Field(foreign_key="reportrun.id")
    delivery_method: str # e.g., "EMAIL", "SLACK"
    destination: str
    delivery_time: datetime = Field(default_factory=datetime.utcnow)
    status: str
    error_message: str | None = None

class ReportArtifact(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_run_id: UUID = Field(foreign_key="reportrun.id")
    artifact_type: str # e.g. "PDF", "CSV"
    storage_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportFilterSet(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_definition_id: UUID = Field(foreign_key="reportdefinition.id")
    filter_config_json: str

class ReportAuditEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agency_id: UUID = Field(foreign_key="agency.id")
    report_run_id: UUID = Field(foreign_key="reportrun.id")
    event_time: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    details: str

