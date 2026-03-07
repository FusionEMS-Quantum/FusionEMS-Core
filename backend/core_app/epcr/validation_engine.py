"""
Clinical Validation Engine — deterministic, rule-based safety checks.

Rules are organized into severity tiers:
  BLOCKING  — hard stop; chart cannot be locked until resolved
  WARNING   — informational; crew must acknowledge but can proceed

No AI is involved. These are explicit, auditable medical logic rules.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core_app.epcr.chart_model import (
    ClinicalValidationIssue,
    ValidationStatus,
)

if TYPE_CHECKING:
    from core_app.epcr.chart_model import Chart


# ─────────────────────────────────────────────────────────────
# Plausible vital ranges (adult defaults; pediatric checked separately)
# ─────────────────────────────────────────────────────────────
_HR_MIN = 0
_HR_MAX = 300
_RR_MIN = 0
_RR_MAX = 80
_SPO2_MIN = 0
_SPO2_MAX = 100
_SBP_MIN = 0
_SBP_MAX = 300
_DBP_MIN = 0
_DBP_MAX = 200
_TEMP_MIN_C = 25.0  # severe hypothermia lower bound
_TEMP_MAX_C = 43.5  # incompatible with life upper bound
_ETCO2_MIN = 0
_ETCO2_MAX = 100
_GLUCOSE_MIN = 0
_GLUCOSE_MAX = 2000
_PAIN_MIN = 0
_PAIN_MAX = 10

# GCS components
_GCS_EYE_MIN, _GCS_EYE_MAX = 1, 4
_GCS_VERBAL_MIN, _GCS_VERBAL_MAX = 1, 5
_GCS_MOTOR_MIN, _GCS_MOTOR_MAX = 1, 6

# Medications with known max single-dose thresholds (dose_unit → max_value)
# These are intentionally conservative; validation warns, not blocks.
_MED_DOSE_WARNINGS: dict[str, dict[str, float]] = {
    "epinephrine": {"mg": 1.0},
    "adenosine": {"mg": 12.0},
    "amiodarone": {"mg": 300.0},
    "atropine": {"mg": 3.0},
    "midazolam": {"mg": 10.0},
    "fentanyl": {"mcg": 200.0, "ug": 200.0},
    "morphine": {"mg": 10.0},
    "naloxone": {"mg": 2.0},
    "dextrose": {"g": 50.0},
    "diphenhydramine": {"mg": 50.0},
    "ondansetron": {"mg": 4.0},
    "nitroglycerin": {"mg": 0.8},
    "aspirin": {"mg": 325.0},
    "ketorolac": {"mg": 30.0},
    "ketamine": {"mg": 500.0},
}


def _issue(rule_id: str, severity: str, message: str, field_path: str = "") -> ClinicalValidationIssue:
    return ClinicalValidationIssue(
        rule_id=rule_id,
        severity=severity,
        message=message,
        field_path=field_path,
    )


def _blocking(rule_id: str, message: str, field_path: str = "") -> ClinicalValidationIssue:
    return _issue(rule_id, "blocking", message, field_path)


def _warning(rule_id: str, message: str, field_path: str = "") -> ClinicalValidationIssue:
    return _issue(rule_id, "warning", message, field_path)


def _parse_dt(ts: str) -> datetime | None:
    if not ts:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


class ValidationEngine:
    """
    Runs deterministic clinical validation rules against a Chart object.

    Returns (ValidationStatus, list[ClinicalValidationIssue]).

    Callers must treat VALIDATION_BLOCKED as a hard lock gate.
    """

    def validate_chart(self, chart: "Chart") -> tuple[ValidationStatus, list[ClinicalValidationIssue]]:
        issues: list[ClinicalValidationIssue] = []
        issues.extend(self._check_required_sections(chart))
        issues.extend(self._check_patient_demographics(chart))
        issues.extend(self._check_dispatch_timestamps(chart))
        issues.extend(self._check_vitals(chart))
        issues.extend(self._check_medications(chart))
        issues.extend(self._check_procedures(chart))
        issues.extend(self._check_disposition(chart))
        issues.extend(self._check_signatures(chart))
        issues.extend(self._check_timeline_integrity(chart))

        blocking = [i for i in issues if i.severity == "blocking"]
        warnings = [i for i in issues if i.severity == "warning"]

        if blocking:
            return ValidationStatus.VALIDATION_BLOCKED, issues
        if warnings:
            return ValidationStatus.VALIDATION_WARNING, issues
        return ValidationStatus.VALIDATION_PASSED, issues

    # ─────────────────────────────────────────────────────────
    # Required section presence
    # ─────────────────────────────────────────────────────────
    def _check_required_sections(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        if not chart.vitals:
            issues.append(_blocking("REQUIRED_VITALS", "At least one vital set is required before locking.", "vitals"))
        if not chart.assessments:
            issues.append(_blocking("REQUIRED_ASSESSMENT", "At least one assessment is required before locking.", "assessments"))
        if not chart.disposition or not chart.disposition.destination_name:
            issues.append(_blocking("REQUIRED_DESTINATION", "Destination/transport disposition must be documented.", "disposition.destination_name"))
        return issues

    # ─────────────────────────────────────────────────────────
    # Patient demographics
    # ─────────────────────────────────────────────────────────
    def _check_patient_demographics(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        p = chart.patient
        if not p.last_name and not p.first_name:
            issues.append(_warning("PATIENT_NAME", "Patient name not recorded. Document if known or mark as unknown.", "patient.last_name"))
        if not p.dob and p.age is None:
            issues.append(_warning("PATIENT_AGE_DOB", "Patient date of birth or age not documented.", "patient.dob"))
        return issues

    # ─────────────────────────────────────────────────────────
    # Dispatch timestamps
    # ─────────────────────────────────────────────────────────
    def _check_dispatch_timestamps(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        d = chart.dispatch
        if not d.psap_call_time and not d.unit_notified_time:
            issues.append(_blocking("DISPATCH_TIME_MISSING", "Dispatch/PSAP call time is required.", "dispatch.psap_call_time"))
        if not d.arrived_scene_time:
            issues.append(_blocking("SCENE_ARRIVAL_MISSING", "Scene arrival time is required.", "dispatch.arrived_scene_time"))
        if not d.departed_scene_time and not d.arrived_destination_time:
            issues.append(_warning("TRANSPORT_TIME_MISSING", "Departed scene or arrived-destination time not recorded.", "dispatch.departed_scene_time"))

        # Chronological order checks (using whichever fields are populated)
        ordered_fields: list[tuple[str, str, str]] = [
            ("psap_call_time", "unit_enroute_time", "DISPATCH_ENROUTE_ORDER"),
            ("unit_enroute_time", "arrived_scene_time", "ENROUTE_SCENE_ORDER"),
            ("arrived_scene_time", "departed_scene_time", "SCENE_DEPART_ORDER"),
            ("departed_scene_time", "arrived_destination_time", "DEPART_ARRIVE_ORDER"),
            ("arrived_destination_time", "transfer_of_care_time", "ARRIVE_TRANSFER_ORDER"),
        ]
        for a_attr, b_attr, rule_id in ordered_fields:
            a_val = getattr(d, a_attr, "")
            b_val = getattr(d, b_attr, "")
            a_ts = _parse_dt(a_val)
            b_ts = _parse_dt(b_val)
            if a_ts and b_ts and b_ts < a_ts:
                issues.append(_blocking(
                    rule_id,
                    f"Timestamp order error: {b_attr} ({b_val}) is before {a_attr} ({a_val}).",
                    f"dispatch.{b_attr}",
                ))
        return issues

    # ─────────────────────────────────────────────────────────
    # Vitals plausibility
    # ─────────────────────────────────────────────────────────
    def _check_vitals(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        for idx, v in enumerate(chart.vitals):
            base = f"vitals[{idx}]"

            if v.heart_rate is not None:
                if not (_HR_MIN <= v.heart_rate <= _HR_MAX):
                    issues.append(_blocking("VITALS_HR_RANGE", f"Heart rate {v.heart_rate} bpm is outside plausible range (0–300).", f"{base}.heart_rate"))

            if v.respiratory_rate is not None:
                if not (_RR_MIN <= v.respiratory_rate <= _RR_MAX):
                    issues.append(_blocking("VITALS_RR_RANGE", f"Respiratory rate {v.respiratory_rate} is outside plausible range (0–80).", f"{base}.respiratory_rate"))

            if v.spo2 is not None:
                if not (_SPO2_MIN <= v.spo2 <= _SPO2_MAX):
                    issues.append(_blocking("VITALS_SPO2_RANGE", f"SpO2 {v.spo2}% is outside valid range (0–100).", f"{base}.spo2"))

            if v.systolic_bp is not None:
                if not (_SBP_MIN <= v.systolic_bp <= _SBP_MAX):
                    issues.append(_blocking("VITALS_SBP_RANGE", f"Systolic BP {v.systolic_bp} mmHg is outside plausible range.", f"{base}.systolic_bp"))
                if v.diastolic_bp is not None and v.diastolic_bp >= v.systolic_bp:
                    issues.append(_blocking("VITALS_BP_ORDER", f"Diastolic BP {v.diastolic_bp} ≥ systolic {v.systolic_bp}. Verify BP values.", f"{base}.diastolic_bp"))

            if v.temperature_c is not None:
                if not (_TEMP_MIN_C <= v.temperature_c <= _TEMP_MAX_C):
                    issues.append(_warning("VITALS_TEMP_RANGE", f"Temperature {v.temperature_c}°C is outside plausible range (25–43.5°C). Verify units.", f"{base}.temperature_c"))

            if v.etco2 is not None:
                if not (_ETCO2_MIN <= v.etco2 <= _ETCO2_MAX):
                    issues.append(_warning("VITALS_ETCO2_RANGE", f"ETCO2 {v.etco2} mmHg is outside plausible range.", f"{base}.etco2"))

            if v.glucose is not None:
                if not (_GLUCOSE_MIN <= v.glucose <= _GLUCOSE_MAX):
                    issues.append(_warning("VITALS_GLUCOSE_RANGE", f"Blood glucose {v.glucose} is outside plausible range.", f"{base}.glucose"))

            if v.pain_scale is not None:
                if not (_PAIN_MIN <= v.pain_scale <= _PAIN_MAX):
                    issues.append(_blocking("VITALS_PAIN_RANGE", f"Pain scale {v.pain_scale} is outside valid range (0–10).", f"{base}.pain_scale"))

            # GCS component vs total check
            if v.gcs_eye is not None and v.gcs_verbal is not None and v.gcs_motor is not None:
                component_sum = v.gcs_eye + v.gcs_verbal + v.gcs_motor
                if v.gcs_total is not None and v.gcs_total != component_sum:
                    issues.append(_blocking(
                        "VITALS_GCS_SUM",
                        f"GCS total {v.gcs_total} does not match component sum {component_sum} (E{v.gcs_eye}+V{v.gcs_verbal}+M{v.gcs_motor}).",
                        f"{base}.gcs_total",
                    ))
                # Individual component range checks
                if not (_GCS_EYE_MIN <= v.gcs_eye <= _GCS_EYE_MAX):
                    issues.append(_blocking("VITALS_GCS_EYE", f"GCS Eye {v.gcs_eye} is outside valid range (1–4).", f"{base}.gcs_eye"))
                if not (_GCS_VERBAL_MIN <= v.gcs_verbal <= _GCS_VERBAL_MAX):
                    issues.append(_blocking("VITALS_GCS_VERBAL", f"GCS Verbal {v.gcs_verbal} is outside valid range (1–5).", f"{base}.gcs_verbal"))
                if not (_GCS_MOTOR_MIN <= v.gcs_motor <= _GCS_MOTOR_MAX):
                    issues.append(_blocking("VITALS_GCS_MOTOR", f"GCS Motor {v.gcs_motor} is outside valid range (1–6).", f"{base}.gcs_motor"))

            if not v.recorded_at:
                issues.append(_warning("VITALS_TIMESTAMP", f"Vital set {idx + 1} is missing a recorded timestamp.", f"{base}.recorded_at"))

        return issues

    # ─────────────────────────────────────────────────────────
    # Medications
    # ─────────────────────────────────────────────────────────
    def _check_medications(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        for idx, m in enumerate(chart.medications):
            base = f"medications[{idx}]"
            if m.prior_to_our_care:
                continue  # Pre-hospital meds — informational only; skip clinical checks
            if not m.medication_name:
                issues.append(_blocking("MED_NAME_MISSING", f"Medication #{idx + 1} has no name documented.", f"{base}.medication_name"))
            if not m.route:
                issues.append(_warning("MED_ROUTE_MISSING", f"Medication '{m.medication_name or idx + 1}' is missing a route of administration.", f"{base}.route"))
            if not m.time_given:
                issues.append(_warning("MED_TIME_MISSING", f"Medication '{m.medication_name or idx + 1}' is missing a time administered.", f"{base}.time_given"))
            if not m.given_by:
                issues.append(_warning("MED_GIVEN_BY", f"Medication '{m.medication_name or idx + 1}' is missing who administered it.", f"{base}.given_by"))

            # Dose range warnings
            med_name_lower = (m.medication_name or "").lower().strip()
            for known_name, thresholds in _MED_DOSE_WARNINGS.items():
                if known_name in med_name_lower:
                    unit_lower = (m.dose_unit or "").lower().strip()
                    if unit_lower in thresholds and m.dose:
                        try:
                            dose_val = float(m.dose)
                            max_val = thresholds[unit_lower]
                            if dose_val > max_val:
                                issues.append(_warning(
                                    "MED_DOSE_HIGH",
                                    f"{m.medication_name} dose {m.dose} {m.dose_unit} exceeds typical single-dose max ({max_val} {m.dose_unit}). Verify intentional.",
                                    f"{base}.dose",
                                ))
                        except (ValueError, TypeError):
                            pass
                    break

        return issues

    # ─────────────────────────────────────────────────────────
    # Procedures
    # ─────────────────────────────────────────────────────────
    def _check_procedures(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        for idx, p in enumerate(chart.procedures):
            base = f"procedures[{idx}]"
            if not p.procedure_name:
                issues.append(_blocking("PROC_NAME_MISSING", f"Procedure #{idx + 1} has no name documented.", f"{base}.procedure_name"))
            if not p.time_performed:
                issues.append(_warning("PROC_TIME_MISSING", f"Procedure '{p.procedure_name or idx + 1}' is missing a time performed.", f"{base}.time_performed"))
            if not p.performed_by:
                issues.append(_warning("PROC_PERFORMED_BY", f"Procedure '{p.procedure_name or idx + 1}' is missing who performed it.", f"{base}.performed_by"))
            if p.attempts < 1:
                issues.append(_warning("PROC_ATTEMPTS", f"Procedure '{p.procedure_name or idx + 1}' has attempts < 1.", f"{base}.attempts"))
        return issues

    # ─────────────────────────────────────────────────────────
    # Disposition / destination
    # ─────────────────────────────────────────────────────────
    def _check_disposition(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        d = chart.disposition
        if not d.patient_disposition_code and not d.transport_disposition:
            issues.append(_warning("DISP_CONDITION", "Patient disposition code/condition not documented.", "disposition.patient_disposition_code"))
        if not d.transport_mode:
            issues.append(_warning("DISP_TRANSPORT_MODE", "Transport mode (e.g., emergency/routine) not documented.", "disposition.transport_mode"))
        return issues

    # ─────────────────────────────────────────────────────────
    # Signatures
    # ─────────────────────────────────────────────────────────
    def _check_signatures(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        if not chart.signatures:
            issues.append(_warning("SIGNATURE_MISSING", "No signatures captured. At minimum, a crew member signature is recommended.", "signatures"))
        else:
            crew_sig = any(
                s.signer_role.lower() in ("crew", "emt", "paramedic", "provider", "author") for s in chart.signatures
            )
            if not crew_sig:
                issues.append(_warning("SIGNATURE_NO_CREW", "No crew/provider signature captured.", "signatures"))
        return issues

    # ─────────────────────────────────────────────────────────
    # Timeline integrity (vitals and meds relative to dispatch)
    # ─────────────────────────────────────────────────────────
    def _check_timeline_integrity(self, chart: "Chart") -> list[ClinicalValidationIssue]:
        issues: list[ClinicalValidationIssue] = []
        dispatch_ts = _parse_dt(chart.dispatch.psap_call_time or chart.dispatch.unit_notified_time)
        if not dispatch_ts:
            return issues  # Can't check relative times without dispatch anchor

        # Check vitals recorded before dispatch
        for idx, v in enumerate(chart.vitals):
            if not v.recorded_at:
                continue
            vts = _parse_dt(v.recorded_at)
            dispatch_anchor = chart.dispatch.psap_call_time or chart.dispatch.unit_notified_time
            if vts and vts < dispatch_ts:
                issues.append(_warning(
                    "TIMELINE_VITALS_BEFORE_DISPATCH",
                    f"Vital set {idx + 1} recorded ({v.recorded_at}) before dispatch time ({dispatch_anchor}). Verify if pre-call.", 
                    f"vitals[{idx}].recorded_at",
                ))

        # Check medications given before dispatch
        for idx, m in enumerate(chart.medications):
            if m.prior_to_our_care or not m.time_given:
                continue
            mts = _parse_dt(m.time_given)
            dispatch_anchor = chart.dispatch.psap_call_time or chart.dispatch.unit_notified_time
            if mts and mts < dispatch_ts:
                issues.append(_warning(
                    "TIMELINE_MED_BEFORE_DISPATCH",
                    f"Medication '{m.medication_name}' time given ({m.time_given}) is before dispatch ({dispatch_anchor}). Confirm if prior to care.",
                    f"medications[{idx}].time_given",
                ))

        return issues
