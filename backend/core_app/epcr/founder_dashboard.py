from __future__ import annotations

from dataclasses import dataclass

from backend.core_app.epcr.chart_model import ChartStatus, NemsisStatus, QAStatus


@dataclass
class DashboardMetrics:
    total_charts_today: int = 0
    sync_backlog: int = 0
    sync_failures: int = 0
    qa_backlog: int = 0
    billing_blocked: int = 0
    nemsis_failures: int = 0
    
@dataclass
class ClinicalAction:
    action_type: str = "" # "QA", "SIGNATURE", "SYNC", "BILLING"
    priority: str = "high"
    title: str = ""
    chart_id: str = ""
    description: str = ""

class FounderClinicalCommand:
    def __init__(self, db_session=None):
        self.db = db_session

    def get_metrics(self, tenant_id: str) -> DashboardMetrics:
        """
        Get high-level clinical metrics for the dashboard.
        """
        # In a real implementation, these would be DB queries
        # e.g. self.db.query(Chart).filter(...)
        
        return DashboardMetrics(
            total_charts_today=42,
            sync_backlog=3,
            sync_failures=1,
            qa_backlog=12,
            billing_blocked=5,
            nemsis_failures=2
        )

    def get_top_actions(self, tenant_id: str, limit: int = 3) -> list[ClinicalAction]:
        """
        Get the top recommended clinical actions.
        """
        # Logic to prioritize actions
        actions = []
        
        # Example 1: Sync Failure
        actions.append(ClinicalAction(
            action_type="SYNC",
            priority="blocking",
            title="Resolve Sync Conflict",
            chart_id="chart-123",
            description="Chart #1052 has a sync conflict with station data."
        ))
        
        # Example 2: QA Backlog
        actions.append(ClinicalAction(
            action_type="QA",
            priority="high",
            title="Review High Acuity Chart",
            chart_id="chart-456",
            description="Cardiac Arrest chart #1048 needs QA review."
        ))

        # Example 3: NEMSIS Error
        actions.append(ClinicalAction(
            action_type="NEMSIS",
            priority="high",
            title="Fix NEMSIS Validation",
            chart_id="chart-789",
            description="Chart #1042 failed export due to missing DOB."
        ))
        
        return actions[:limit]

    def get_chart_status_breakdown(self, tenant_id: str) -> dict[str, int]:
        """
        Return count of charts in each status.
        """
        return {
            ChartStatus.IN_PROGRESS: 15,
            ChartStatus.CLINICAL_REVIEW_REQUIRED: 8,
            ChartStatus.READY_FOR_LOCK: 5,
            ChartStatus.LOCKED: 20
        }
