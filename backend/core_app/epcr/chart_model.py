from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ChartMode(StrEnum):
    BLS = "bls"
    ACLS = "acls"
    CCT = "cct"
    HEMS = "hems"
    FIRE = "fire"


class ChartStatus(StrEnum):
    CHART_CREATED = "chart_created"
    IN_PROGRESS = "in_progress"
    OFFLINE_PENDING_SYNC = "offline_pending_sync"
    SYNC_IN_PROGRESS = "sync_in_progress"
    SYNC_FAILED = "sync_failed"
    SYNCED = "synced"
    CLINICAL_REVIEW_REQUIRED = "clinical_review_required"
    READY_FOR_LOCK = "ready_for_lock"
    LOCKED = "locked"
    AMENDMENT_REQUESTED = "amendment_requested"
    AMENDED = "amended"
    CLOSED = "closed"
    # Legacy mappings if needed, can be deprecated
    DRAFT = "draft"
    PENDING_QA = "pending_qa"
    SUBMITTED = "submitted"
    EXPORTED = "exported"
    VOID = "void"
    CANCELLED = "cancelled"


class SyncStatus(StrEnum):
    LOCAL_ONLY = "local_only"
    QUEUED_FOR_SYNC = "queued_for_sync"
    SYNCING = "syncing"
    SYNC_ERROR = "sync_error"
    PARTIAL_SYNC = "partial_sync"
    FULLY_SYNCED = "fully_synced"
    CONFLICT_REVIEW_REQUIRED = "conflict_review_required"
    # Legacy
    SYNCED = "synced"
    CONFLICT = "conflict"
    PENDING_SYNC = "pending_sync"


class ValidationStatus(StrEnum):
    VALIDATION_PENDING = "validation_pending"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_WARNING = "validation_warning"
    VALIDATION_BLOCKED = "validation_blocked"
    REVIEW_REQUIRED = "review_required"


class QAStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    IN_REVIEW = "in_review"
    NEEDS_CORRECTION = "needs_correction"
    CORRECTION_SUBMITTED = "correction_submitted"
    APPROVED = "approved"
    ESCALATED = "escalated"
    EDUCATION_FLAGGED = "education_flagged"
    CLOSED = "closed"


class NemsisStatus(StrEnum):
    NOT_READY = "not_ready"
    READY_FOR_EXPORT = "ready_for_export"
    EXPORT_QUEUED = "export_queued"
    EXPORTING = "exporting"
    EXPORT_FAILED = "export_failed"
    EXPORT_COMPLETE = "export_complete"
    REJECTED_BY_RECEIVER = "rejected_by_receiver"
    NEEDS_CORRECTION = "needs_correction"


class HandoffStatus(StrEnum):
    HANDOFF_NOT_PREPARED = "handoff_not_prepared"
    HANDOFF_DRAFTED = "handoff_drafted"
    HANDOFF_READY = "handoff_ready"
    HANDOFF_SENT = "handoff_sent"
    HANDOFF_FAILED = "handoff_failed"
    HANDOFF_CONFIRMED = "handoff_confirmed"


@dataclass
class PatientDemographics:
    first_name: str = ""
    last_name: str = ""
    dob: str = ""
    age: int | None = None
    age_units: str = ""  # Years, Months, Days
    gender: str = ""
    race: str = ""
    ssn_last4: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    mrn: str = ""
    insurance_id: str = ""
    insurance_group: str = ""
    insurance_payer: str = ""
    weight_kg: float | None = None
    height_cm: float | None = None


@dataclass
class ConsentRecord:
    consent_type: str = ""
    consented_by: str = ""
    consent_time: str = ""
    refusal_reason: str = ""
    capacity_confirmed: bool = False
    risks_explained: bool = False
    signature_attachment_id: str = ""


@dataclass
class DispatchInfo:
    incident_number: str = ""
    psap_call_time: str = ""
    unit_notified_time: str = ""
    unit_enroute_time: str = ""
    arrived_scene_time: str = ""
    patient_contact_time: str = ""
    departed_scene_time: str = ""
    arrived_destination_time: str = ""
    transfer_of_care_time: str = ""
    call_type_code: str = ""
    complaint_reported: str = ""
    priority_level: str = ""
    cad_incident_id: str = ""
    responding_unit: str = ""
    crew_members: list[str] = field(default_factory=list)


@dataclass
class VitalSet:
    vital_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: str = ""
    recorded_by: str = ""
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    spo2: float | None = None
    etco2: float | None = None
    glucose: float | None = None
    gcs_eye: int | None = None
    gcs_verbal: int | None = None
    gcs_motor: int | None = None
    gcs_total: int | None = None
    temperature_c: float | None = None
    pain_scale: int | None = None
    pupils_left: str = ""
    pupils_right: str = ""
    skin_color: str = ""
    skin_temp: str = ""
    skin_moisture: str = ""
    rhythm: str = ""
    rhythm_attachment_id: str = ""
    weight_kg: float | None = None


@dataclass
class MedicationAdmin:
    med_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    medication_name: str = ""
    dose: str = ""
    dose_unit: str = ""
    route: str = ""
    time_given: str = ""
    given_by: str = ""
    indication: str = ""
    lot_number: str = ""
    expiration: str = ""
    prior_to_our_care: bool = False
    attachment_id: str = ""


@dataclass
class ProcedurePerformed:
    proc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    procedure_name: str = ""
    procedure_code: str = ""
    time_performed: str = ""
    performed_by: str = ""
    attempts: int = 1
    successful: bool = True
    complications: str = ""
    confirmation_method: str = ""
    prior_to_our_care: bool = False
    attachment_id: str = ""


@dataclass
class AssessmentBlock:
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assessment_type: str = "primary"
    time: str = ""
    performed_by: str = ""
    chief_complaint: str = ""
    hpi: str = ""
    history: str = ""
    allergies: list[str] = field(default_factory=list)
    medications_home: list[str] = field(default_factory=list)
    airway_status: str = ""
    breathing_status: str = ""
    circulation_status: str = ""
    neuro_status: str = ""
    trauma_findings: dict[str, Any] = field(default_factory=dict)
    medical_findings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class DispositionInfo:
    patient_disposition_code: str = ""
    transport_disposition: str = ""
    destination_name: str = ""
    destination_id: str = ""
    room_number: str = ""
    transferred_to_name: str = ""
    transport_mode: str = ""
    level_of_care: str = ""
    reason_not_transported: str = ""
    signature_attachment_id: str = ""


@dataclass
class ACLSBlock:
    code_start_time: str = ""
    rosc_time: str = ""
    termination_time: str = ""
    initial_rhythm: str = ""
    final_rhythm: str = ""
    defibrillation_events: list[dict[str, Any]] = field(default_factory=list)
    pacing_events: list[dict[str, Any]] = field(default_factory=list)
    total_shocks: int = 0


@dataclass
class CCTBlock:
    drips: list[dict[str, Any]] = field(default_factory=list)
    vent_settings: dict[str, Any] = field(default_factory=dict)
    infusion_programs: list[dict[str, Any]] = field(default_factory=list)
    hemodynamics_trend: list[dict[str, Any]] = field(default_factory=list)
    transfer_source_facility: str = ""
    transfer_source_unit: str = ""
    receiving_facility: str = ""


@dataclass
class HEMSBlock:
    wheels_up_time: str = ""
    wheels_down_time: str = ""
    mission_number: str = ""
    aircraft_id: str = ""
    lz_coords: dict[str, Any] = field(default_factory=dict)
    flight_crew: list[str] = field(default_factory=list)
    flight_time_minutes: float | None = None
    handoff_summary: str = ""


@dataclass
class ProvenanceRecord:
    field_name: str = ""
    value: Any = None
    source_type: str = "manual"
    source_attachment_id: str = ""
    confidence: float = 1.0
    confirmed_by: str = ""
    confirmed_at: str = ""
    bounding_box: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClinicalSignature:
    signature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signer_name: str = ""
    signer_role: str = ""  # e.g., "Patient", "Crew", "Facility"
    signature_type: str = ""  # e.g., "HIPAA", "Refusal", "Treatment"
    timestamp: str = ""
    data_points: str = ""  # Encoded signature data
    is_valid: bool = False


@dataclass
class ClinicalTimelineEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    timestamp: str = ""
    event_type: str = "" # VITAL, MED, PROC, STATUS_CHANGE, SYNC, LOCK
    description: str = ""
    actor_id: str = ""
    source: str = "user" # user, device, system
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ClinicalAttachment:
    attachment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    file_name: str = ""
    file_type: str = "" # image/jpeg, application/pdf
    file_size_bytes: int = 0
    storage_path: str = ""
    uploaded_at: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ClinicalAmendmentRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    requested_by: str = ""
    reason: str = ""
    requested_at: str = ""
    status: str = "pending"  # pending, approved, rejected
    original_value: str = ""
    proposed_value: str = ""
    field_path: str = ""


@dataclass
class AINarrativeDraft:
    draft_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    generated_at: str = ""
    model_version: str = ""
    narrative_text: str = ""
    confidence_score: float = 0.0
    contradictions_found: list[str] = field(default_factory=list)
    missing_elements: list[str] = field(default_factory=list)
    is_accepted: bool = False


@dataclass
class QAFlag:
    flag_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    flag_type: str = ""  # PROTOCOL_DEVIATION, DOCUMENTATION_ERROR, CLINICAL_RISK
    severity: str = "medium"
    description: str = ""
    flagged_by: str = ""  # "AI" or "Human"
    resolved: bool = False


@dataclass
class QAReview:
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    reviewer_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = QAStatus.NOT_REVIEWED
    flags: list[QAFlag] = field(default_factory=list)
    notes: str = ""
    decision: str = ""


@dataclass
class ClinicalValidationIssue:
    issue_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    severity: str = "warning"  # blocking, warning
    message: str = ""
    field_path: str = ""


@dataclass
class NemsisValidationIssue:
    issue_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nemsis_element: str = ""
    message: str = ""
    severity: str = "error"


@dataclass
class ClinicalHandoffPacket:
    packet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    generated_at: str = ""
    recipient_facility: str = ""
    content_summary: str = ""
    delivery_status: str = HandoffStatus.HANDOFF_NOT_PREPARED
    delivery_method: str = ""  # fax, direct, email


@dataclass
class NemsisExportRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    export_format: str = "xml"
    exported_at: str = ""
    status: str = NemsisStatus.NOT_READY
    validation_issues: list[NemsisValidationIssue] = field(default_factory=list)
    xml_content: str = ""


@dataclass
class NemsisExportBatch:
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    created_at: str = ""
    records: list[NemsisExportRecord] = field(default_factory=list)
    status: str = NemsisStatus.NOT_READY
    submission_response: str = ""


@dataclass
class QAQueueItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chart_id: str = ""
    patient_name: str = ""
    run_date: str = ""
    status: str = QAStatus.NOT_REVIEWED
    assigned_reviewer: str = ""
    priority: str = "medium"


# Aliases
ClinicalContradictionFlag = QAFlag


def _build_dataclass(cls, raw: dict) -> object:
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name in raw:
            kwargs[f.name] = raw[f.name]
        elif f.default is not dataclasses.MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:
            kwargs[f.name] = f.default_factory()
        else:
            kwargs[f.name] = None
    return cls(**kwargs)


@dataclass
class Chart:
    chart_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    resource_pack_id: str | None = None
    chart_mode: str = ChartMode.BLS.value
    chart_status: str = ChartStatus.DRAFT.value
    sync_status: str = SyncStatus.PENDING_SYNC.value
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_by: str = ""
    last_modified_by: str = ""
    patient: PatientDemographics = field(default_factory=PatientDemographics)
    consent: ConsentRecord = field(default_factory=ConsentRecord)
    dispatch: DispatchInfo = field(default_factory=DispatchInfo)
    vitals: list[VitalSet] = field(default_factory=list)
    medications: list[MedicationAdmin] = field(default_factory=list)
    procedures: list[ProcedurePerformed] = field(default_factory=list)
    assessments: list[AssessmentBlock] = field(default_factory=list)
    disposition: DispositionInfo = field(default_factory=DispositionInfo)
    acls: ACLSBlock | None = None
    cct: CCTBlock | None = None
    hems: HEMSBlock | None = None
    narrative: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    signatures: list[ClinicalSignature] = field(default_factory=list)
    qa_review: QAReview | None = None
    validation_issues: list[ClinicalValidationIssue] = field(default_factory=list)
    nemsis_issues: list[NemsisValidationIssue] = field(default_factory=list)
    handoff_packet: ClinicalHandoffPacket | None = None
    ai_draft: AINarrativeDraft | None = None
    amendment_requests: list[ClinicalAmendmentRequest] = field(default_factory=list)
    completeness_score: float = 0.0
    completeness_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Chart:
        c = cls.__new__(cls)
        c.chart_id = d.get("chart_id", str(uuid.uuid4()))
        c.tenant_id = d.get("tenant_id", "")
        c.resource_pack_id = d.get("resource_pack_id")
        c.chart_mode = d.get("chart_mode", ChartMode.BLS.value)
        c.chart_status = d.get("chart_status", ChartStatus.DRAFT.value)
        c.sync_status = d.get("sync_status", SyncStatus.PENDING_SYNC.value)
        c.created_at = d.get("created_at", datetime.now(UTC).isoformat())
        c.updated_at = d.get("updated_at", datetime.now(UTC).isoformat())
        c.created_by = d.get("created_by", "")
        c.last_modified_by = d.get("last_modified_by", "")

        c.patient = (
            _build_dataclass(PatientDemographics, d.get("patient", {}))
            if isinstance(d.get("patient"), dict)
            else PatientDemographics()
        )
        c.consent = (
            _build_dataclass(ConsentRecord, d.get("consent", {}))
            if isinstance(d.get("consent"), dict)
            else ConsentRecord()
        )
        c.dispatch = (
            _build_dataclass(DispatchInfo, d.get("dispatch", {}))
            if isinstance(d.get("dispatch"), dict)
            else DispatchInfo()
        )
        c.disposition = (
            _build_dataclass(DispositionInfo, d.get("disposition", {}))
            if isinstance(d.get("disposition"), dict)
            else DispositionInfo()
        )

        c.vitals = [
            _build_dataclass(VitalSet, vs) for vs in d.get("vitals", []) if isinstance(vs, dict)
        ]
        c.medications = [
            _build_dataclass(MedicationAdmin, m)
            for m in d.get("medications", [])
            if isinstance(m, dict)
        ]
        c.procedures = [
            _build_dataclass(ProcedurePerformed, pr)
            for pr in d.get("procedures", [])
            if isinstance(pr, dict)
        ]
        c.assessments = [
            _build_dataclass(AssessmentBlock, a)
            for a in d.get("assessments", [])
            if isinstance(a, dict)
        ]
        c.provenance = [
            _build_dataclass(ProvenanceRecord, pr)
            for pr in d.get("provenance", [])
            if isinstance(pr, dict)
        ]
        c.signatures = [
            _build_dataclass(ClinicalSignature, s)
            for s in d.get("signatures", [])
            if isinstance(s, dict)
        ]
        c.validation_issues = [
            _build_dataclass(ClinicalValidationIssue, v)
            for v in d.get("validation_issues", [])
            if isinstance(v, dict)
        ]
        c.nemsis_issues = [
            _build_dataclass(NemsisValidationIssue, n)
            for n in d.get("nemsis_issues", [])
            if isinstance(n, dict)
        ]
        c.amendment_requests = [
            _build_dataclass(ClinicalAmendmentRequest, ar)
            for ar in d.get("amendment_requests", [])
            if isinstance(ar, dict)
        ]

        qa_d = d.get("qa_review")
        if isinstance(qa_d, dict):
            # QAReview has a list of flags which also needs parsing
            flags = [
                _build_dataclass(QAFlag, f) for f in qa_d.get("flags", []) if isinstance(f, dict)
            ]
            qa_d_copy = dict(qa_d)
            qa_d_copy["flags"] = flags
            c.qa_review = _build_dataclass(QAReview, qa_d_copy)
        else:
            c.qa_review = None

        handoff_d = d.get("handoff_packet")
        c.handoff_packet = (
            _build_dataclass(ClinicalHandoffPacket, handoff_d)
            if isinstance(handoff_d, dict)
            else None
        )

        ai_d = d.get("ai_draft")
        c.ai_draft = _build_dataclass(AINarrativeDraft, ai_d) if isinstance(ai_d, dict) else None

        acls_d = d.get("acls")
        c.acls = _build_dataclass(ACLSBlock, acls_d) if isinstance(acls_d, dict) else None
        cct_d = d.get("cct")
        c.cct = _build_dataclass(CCTBlock, cct_d) if isinstance(cct_d, dict) else None
        hems_d = d.get("hems")
        c.hems = _build_dataclass(HEMSBlock, hems_d) if isinstance(hems_d, dict) else None

        c.narrative = d.get("narrative", "")
        c.attachments = d.get("attachments", [])
        c.completeness_score = d.get("completeness_score", 0.0)
        c.completeness_issues = d.get("completeness_issues", [])
        return c
