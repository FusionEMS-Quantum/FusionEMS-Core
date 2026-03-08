"""Founder operations dashboard service tests.

Covers:
- Deployment issue aggregation
- Patient balance dashboard aggregation
- Top-actions prioritization and limit behavior
- Full summary envelope generation
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from core_app.services.founder_ops_service import FounderOpsService


class _FakeExecuteResult:
    """Mimics SQLAlchemy execute() result surface used in service methods."""

    def __init__(self, *, scalar_value: int | None = None, rows: list[Any] | None = None) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one(self) -> int:
        if self._scalar_value is None:
            raise AssertionError("Expected scalar_one() result but no scalar_value was configured")
        return self._scalar_value

    def scalars(self) -> _FakeExecuteResult:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)


class _FakeDB:
    """Deterministic queue-backed DB execute mock."""

    def __init__(self, queued_results: list[_FakeExecuteResult]) -> None:
        self._queued_results = list(queued_results)
        self.execute_calls = 0

    def execute(self, _query: Any) -> _FakeExecuteResult:
        self.execute_calls += 1
        if not self._queued_results:
            raise AssertionError("No queued execute result left for this query")
        return self._queued_results.pop(0)


def _scalar(value: int) -> _FakeExecuteResult:
    return _FakeExecuteResult(scalar_value=value)


def _rows(value: list[Any]) -> _FakeExecuteResult:
    return _FakeExecuteResult(rows=value)


@dataclass(frozen=True)
class _FailureAuditRow:
    id: str
    what_is_wrong: str
    severity: str
    created_at: datetime | None


class TestFounderOpsService:
    def test_get_deployment_issues_returns_counts_and_recent_failure_shape(self) -> None:
        fake_failure = _FailureAuditRow(
            id="f-001",
            what_is_wrong="Terraform apply timed out",
            severity="HIGH",
            created_at=datetime(2026, 3, 7, 3, 10, tzinfo=UTC),
        )
        fake_db = _FakeDB([
            _rows([object(), object()]),  # failed deployments
            _rows([object()]),  # retrying deployments
            _rows([fake_failure]),  # recent failures
        ])

        service = FounderOpsService(cast(Any, fake_db))
        result = service.get_deployment_issues()

        assert result["failed_deployments"] == 2
        assert result["retrying_deployments"] == 1
        assert len(result["recent_failures"]) == 1

        recent = result["recent_failures"][0]
        assert recent["id"] == "f-001"
        assert recent["what_is_wrong"] == "Terraform apply timed out"
        assert recent["severity"] == "HIGH"
        assert recent["created_at"] == "2026-03-07T03:10:00+00:00"

    def test_get_patient_balance_review_aggregates_counts_and_outstanding_total(self) -> None:
        # open, autopay, payment_plan, collections_ready, sent_to_collections, written_off, total_outstanding
        fake_db = _FakeDB([
            _scalar(11),
            _scalar(4),
            _scalar(3),
            _scalar(2),
            _scalar(1),
            _scalar(5),
            _scalar(987_654),
        ])

        service = FounderOpsService(cast(Any, fake_db))
        result = service.get_patient_balance_review()

        assert result == {
            "open_balances": 11,
            "autopay_pending": 4,
            "payment_plan_active": 3,
            "collections_ready": 2,
            "sent_to_collections": 1,
            "written_off": 5,
            "total_outstanding_cents": 987_654,
        }
        assert fake_db.execute_calls == 7

    def test_get_top_actions_prioritizes_critical_and_limits_to_three(self) -> None:
        # failed_deployments, past_due, ready_to_submit, denied, blocking_issues, escalated, pending_collections
        fake_db = _FakeDB([
            _scalar(1),  # deployment failed
            _scalar(2),  # past due
            _scalar(3),  # ready to submit
            _scalar(4),  # denied
            _scalar(5),  # blocking issues
            _scalar(1),  # escalated paging
            _scalar(9),  # pending collections
        ])

        service = FounderOpsService(cast(Any, fake_db))
        actions = service.get_top_actions()

        assert len(actions) == 3
        assert [a["severity"] for a in actions] == ["critical", "critical", "high"]
        assert actions[0]["domain"] == "deployment"
        assert actions[0]["category"] == "blocking_deployment"
        assert actions[1]["domain"] == "billing"
        assert actions[1]["category"] == "blocking_money"
        assert actions[2]["domain"] in {"payments", "billing"}

    def test_get_ops_summary_includes_all_sections_and_timestamp(self) -> None:
        service = FounderOpsService(cast(Any, object()))

        service.get_deployment_issues = lambda: {"failed_deployments": 1}  # type: ignore[method-assign]
        service.get_payment_failures = lambda: {"past_due_subscriptions": 2}  # type: ignore[method-assign]
        service.get_claims_pipeline = lambda: {"ready_to_submit": 3}  # type: ignore[method-assign]
        service.get_high_risk_denials = lambda: {"high_value_denials": 4}  # type: ignore[method-assign]
        service.get_patient_balance_review = lambda: {"open_balances": 5}  # type: ignore[method-assign]
        service.get_collections_review = lambda: {"pending_reviews": 6}  # type: ignore[method-assign]
        service.get_debt_setoff_review = lambda: {"pending_batches": 7}  # type: ignore[method-assign]
        service.get_profile_gaps = lambda: {"missing_tax_profile": 8}  # type: ignore[method-assign]
        service.get_comms_health = lambda: {"degraded_channels": 1}  # type: ignore[method-assign]
        service.get_crewlink_health = lambda: {"active_alerts": 2}  # type: ignore[method-assign]
        service.get_top_actions = lambda: [{"domain": "deployment", "severity": "critical"}]  # type: ignore[method-assign]

        result = service.get_ops_summary()

        assert result["deployment_issues"] == {"failed_deployments": 1}
        assert result["payment_failures"] == {"past_due_subscriptions": 2}
        assert result["claims_pipeline"] == {"ready_to_submit": 3}
        assert result["high_risk_denials"] == {"high_value_denials": 4}
        assert result["patient_balance_review"] == {"open_balances": 5}
        assert result["collections_review"] == {"pending_reviews": 6}
        assert result["debt_setoff_review"] == {"pending_batches": 7}
        assert result["profile_gaps"] == {"missing_tax_profile": 8}
        assert result["comms_health"] == {"degraded_channels": 1}
        assert result["crewlink_health"] == {"active_alerts": 2}
        assert result["top_actions"] == [{"domain": "deployment", "severity": "critical"}]

        generated_at = result["generated_at"]
        assert isinstance(generated_at, str)
        parsed = datetime.fromisoformat(generated_at)
        assert parsed.tzinfo is not None
