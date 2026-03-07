from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.core_app.epcr.chart_model import (
    Chart,
    NemsisExportRecord,
    NemsisStatus,
    NemsisValidationIssue,
)
from backend.core_app.epcr.nemsis_exporter import NEMSISExporter
from backend.core_app.nemsis.validator import NEMSISValidator, ValidationIssue


class NemsisReadinessService:
    def __init__(self, db_session=None):
        self.db = db_session
        self.exporter = NEMSISExporter()
        self.validator = NEMSISValidator()

    def check_readiness(self, chart: Chart, agency_info: dict) -> NemsisExportRecord:
        """
        Check if a chart is ready for NEMSIS export.
        Generates XML and runs validators.
        """
        # Generate XML
        try:
            xml_bytes = self.exporter.export_chart(chart.to_dict(), agency_info)
            xml_content = xml_bytes.decode("utf-8")
        except Exception as e:
            # Fatal generation error
            return NemsisExportRecord(
                record_id=str(uuid.uuid4()),
                chart_id=chart.chart_id,
                exported_at=datetime.now(UTC).isoformat(),
                status=NemsisStatus.EXPORT_FAILED,
                validation_issues=[
                    NemsisValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        nemsis_element="GENERATION",
                        message=f"XML Generation failed: {str(e)}",
                        severity="error",
                    )
                ],
            )

        # Validate XML
        result = self.validator.validate_xml_bytes(xml_bytes, state_code=agency_info.get("state", "WI"))
        
        issues = []
        for issue in result.issues:
            issues.append(NemsisValidationIssue(
                issue_id=str(uuid.uuid4()),
                nemsis_element=issue.element_id,
                message=issue.plain_message,
                severity=issue.severity,
            ))
            
        status = NemsisStatus.READY_FOR_EXPORT if result.valid else NemsisStatus.NEEDS_CORRECTION
        
        return NemsisExportRecord(
            record_id=str(uuid.uuid4()),
            chart_id=chart.chart_id,
            exported_at=datetime.now(UTC).isoformat(),
            status=status,
            validation_issues=issues,
            xml_content=xml_content,
        )

    def queue_for_export(self, record: NemsisExportRecord) -> bool:
        """
        Queue a valid record for actual submission.
        """
        if record.status != NemsisStatus.READY_FOR_EXPORT:
            return False
            
        record.status = NemsisStatus.EXPORT_QUEUED
        # In real app, push to queue/DB
        return True
