from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.core_app.epcr.chart_model import (
    Chart,
    QAFlag,
    QAQueueItem,
    QAReview,
    QAStatus,
)


class QAService:
    def __init__(self, db_session=None):
        self.db = db_session

    def create_review(self, chart: Chart, reviewer_id: str) -> QAReview:
        """
        Create a new QA review session for a chart.
        """
        review = QAReview(
            review_id=str(uuid.uuid4()),
            chart_id=chart.chart_id,
            reviewer_id=reviewer_id,
            started_at=datetime.now(UTC).isoformat(),
            status=QAStatus.IN_REVIEW,
            flags=[],
        )
        chart.qa_review = review
        # In real app, persist review
        return review

    def flag_issue(self, review: QAReview, description: str, severity: str = "medium") -> QAFlag:
        """
        Add a manual flag during review.
        """
        flag = QAFlag(
            flag_id=str(uuid.uuid4()),
            chart_id=review.chart_id,
            flag_type="MANUAL_REVIEW",
            description=description,
            severity=severity,
            flagged_by=review.reviewer_id,
            resolved=False,
        )
        review.flags.append(flag)
        return flag

    def complete_review(self, review: QAReview, decision: str, notes: str):
        """
        Complete the review session.
        Decision: APPROVED, NEEDS_CORRECTION, ESCALATED
        """
        review.completed_at = datetime.now(UTC).isoformat()
        review.decision = decision
        review.notes = notes
        
        if decision == "APPROVED":
            review.status = QAStatus.APPROVED
        elif decision == "NEEDS_CORRECTION":
            review.status = QAStatus.NEEDS_CORRECTION
        elif decision == "ESCALATED":
            review.status = QAStatus.ESCALATED
        else:
            review.status = QAStatus.CLOSED

    def get_qa_queue(self, tenant_id: str) -> list[QAQueueItem]:
        """
        Get the queue of charts pending QA.
        """
        # Placeholder
        return []
