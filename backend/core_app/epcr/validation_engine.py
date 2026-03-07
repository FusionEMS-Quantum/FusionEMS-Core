from __future__ import annotations

import uuid
from typing import Any

from backend.core_app.epcr.chart_model import (
    Chart,
    ClinicalValidationIssue,
    ValidationStatus,
)


class ValidationEngine:
    def validate_chart(self, chart: Chart) -> tuple[ValidationStatus, list[ClinicalValidationIssue]]:
        issues: list[ClinicalValidationIssue] = []

        # 1. Required Section Completeness
        self._check_required_sections(chart, issues)

        # 2. Timestamp Ordering
        self._check_timestamps(chart, issues)

        # 3. Vitals Plausibility
        self._check_vitals_plausibility(chart, issues)

        # 4. Medication Checks
        self._check_medications(chart, issues)
        
        # 5. Signature Completeness
        self._check_signatures(chart, issues)

        status = ValidationStatus.VALIDATION_PASSED
        if any(i.severity == "blocking" for i in issues):
            status = ValidationStatus.VALIDATION_BLOCKED
        elif issues:
            status = ValidationStatus.VALIDATION_WARNING
        
        return status, issues

    def _create_issue(self, message: str, severity: str, field_path: str) -> ClinicalValidationIssue:
        return ClinicalValidationIssue(
            issue_id=str(uuid.uuid4()),
            rule_id="builtin",
            severity=severity,
            message=message,
            field_path=field_path,
        )

    def _check_required_sections(self, chart: Chart, issues: list[ClinicalValidationIssue]):
        if not chart.patient.first_name or not chart.patient.last_name:
            issues.append(self._create_issue("Patient name is required", "blocking", "patient.name"))
        
        if not chart.narrative or len(chart.narrative) < 10:
             issues.append(self._create_issue("Narrative is too short or missing", "blocking", "narrative"))

    def _check_timestamps(self, chart: Chart, issues: list[ClinicalValidationIssue]):
        # Simplified check
        d = chart.dispatch
        if d.unit_enroute_time and d.unit_notified_time and d.unit_enroute_time < d.unit_notified_time:
             issues.append(self._create_issue("Enroute time cannot be before notified time", "blocking", "dispatch.times"))
        
        if d.arrived_scene_time and d.unit_enroute_time and d.arrived_scene_time < d.unit_enroute_time:
             issues.append(self._create_issue("Scene arrival cannot be before enroute time", "blocking", "dispatch.times"))

    def _check_vitals_plausibility(self, chart: Chart, issues: list[ClinicalValidationIssue]):
        for idx, vital in enumerate(chart.vitals):
            if vital.systolic_bp is not None and (vital.systolic_bp < 30 or vital.systolic_bp > 300):
                issues.append(self._create_issue(f"Systolic BP {vital.systolic_bp} is implausible", "warning", f"vitals[{idx}].systolic_bp"))
            
            if vital.heart_rate is not None and (vital.heart_rate < 0 or vital.heart_rate > 300):
                issues.append(self._create_issue(f"Heart Rate {vital.heart_rate} is implausible", "warning", f"vitals[{idx}].heart_rate"))

    def _check_medications(self, chart: Chart, issues: list[ClinicalValidationIssue]):
        for idx, med in enumerate(chart.medications):
             if not med.dose or not med.dose_unit:
                 issues.append(self._create_issue(f"Medication {med.medication_name} missing dose", "blocking", f"medications[{idx}].dose"))

    def _check_signatures(self, chart: Chart, issues: list[ClinicalValidationIssue]):
        if not chart.signatures:
             issues.append(self._create_issue("At least one signature is required", "blocking", "signatures"))
