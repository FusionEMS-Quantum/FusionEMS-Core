from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from backend.core_app.epcr.chart_model import (
    Chart,
    ChartStatus,
    ClinicalAmendmentRequest,
    ClinicalSignature,
    ClinicalValidationIssue,
    ValidationStatus,
)


class ChartService:
    def __init__(self, db_session=None):
        self.db = db_session  # Placeholder for DB session

    def create_chart(
        self,
        tenant_id: str,
        created_by: str,
        dispatch_info: dict[str, Any] | None = None,
    ) -> Chart:
        """
        Create a new clinical chart linked to an incident if dispatch info provided.
        """
        chart = Chart(
            chart_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by=created_by,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            chart_status=ChartStatus.CHART_CREATED,
        )

        if dispatch_info:
            # Populate dispatch info from dict
            pass  # Logic to map dispatch info would go here

        # TODO: Persist to DB
        return chart

    def lock_chart(self, chart: Chart, user_id: str) -> tuple[bool, list[ClinicalValidationIssue]]:
        """
        Attempt to lock the chart.
        Returns (success, issues).
        """
        # 1. Check for blocking validation issues
        blocking_issues = [i for i in chart.validation_issues if i.severity == "blocking"]
        if blocking_issues:
            return False, blocking_issues

        # 2. Check for critical missing signatures (if not handled by validation)
        # 3. Check for sync status (must be fully synced?) - Maybe not strictly required for lock but good practice

        # Apply Lock
        chart.chart_status = ChartStatus.LOCKED
        chart.last_modified_by = user_id
        chart.updated_at = datetime.now(UTC).isoformat()
        
        # Log event
        # self.log_event(chart.chart_id, "CHART_LOCKED", user_id)

        return True, []

    def request_amendment(
        self, chart: Chart, user_id: str, reason: str, field_path: str
    ) -> ClinicalAmendmentRequest:
        """
        Request an amendment for a locked chart.
        """
        if chart.chart_status != ChartStatus.LOCKED:
            raise ValueError("Chart must be locked to request amendment")

        request = ClinicalAmendmentRequest(
            chart_id=chart.chart_id,
            requested_by=user_id,
            reason=reason,
            requested_at=datetime.now(UTC).isoformat(),
            field_path=field_path,
            status="pending",
        )
        
        chart.amendment_requests.append(request)
        chart.chart_status = ChartStatus.AMENDMENT_REQUESTED
        chart.updated_at = datetime.now(UTC).isoformat()
        
        return request

    def approve_amendment(self, chart: Chart, request_id: str, approver_id: str) -> bool:
        """
        Approve an amendment request, unlocking the chart for that specific field or generally.
        """
        for req in chart.amendment_requests:
            if req.request_id == request_id and req.status == "pending":
                req.status = "approved"
                # Logic to unlock chart or enable editing
                chart.chart_status = ChartStatus.AMENDED
                # Log approval
                return True
        return False

    def sign_chart(
        self, chart: Chart, signer_name: str, role: str, signature_data: str
    ) -> ClinicalSignature:
        """
        Add a signature to the chart.
        """
        sig = ClinicalSignature(
            signer_name=signer_name,
            signer_role=role,
            timestamp=datetime.now(UTC).isoformat(),
            data_points=signature_data,
            is_valid=True,
        )
        chart.signatures.append(sig)
        chart.updated_at = datetime.now(UTC).isoformat()
        return sig
