"""Founder command domain service tests.

Covers:
- Specialty ops summary counts/action prioritization
- Records command summary counts/action prioritization
- Integration command summary counts/action prioritization
- Read-list passthrough behavior for failed sync jobs
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, cast

from core_app.core.errors import AppError
from core_app.models.integration_connectors import ConnectorInstallState
from core_app.schemas.founder_command_domains import FounderCommandAction
from core_app.services.founder_command_domain_service import FounderCommandDomainService


class _FakeExecuteResult:
    """Mimics SQLAlchemy execute() result surface used in service methods."""

    def __init__(self, *, scalar_value: Any = None, rows: list[Any] | None = None) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar_one(self) -> int:
        if self._scalar_value is None:
            raise AssertionError("Expected scalar_one() but no scalar value was configured")
        return cast(int, self._scalar_value)

    def scalar_one_or_none(self) -> Any:
        return self._scalar_value

    def scalars(self) -> _FakeExecuteResult:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)


class _FakeQuery:
    def __init__(self, db: _FakeDB) -> None:
        self._db = db

    def filter(self, *_criteria: Any) -> _FakeQuery:
        return self

    def count(self) -> int:
        result = self._db.execute(None)
        return result.scalar_one()


class _FakeDB:
    """Deterministic queue-backed DB execute mock."""

    def __init__(self, queued_results: list[_FakeExecuteResult]) -> None:
        self._queued_results = list(queued_results)
        self.execute_calls = 0
        self.added: list[Any] = []
        self.flush_calls = 0

    def execute(self, _query: Any) -> _FakeExecuteResult:
        self.execute_calls += 1
        if not self._queued_results:
            raise AssertionError("No queued execute result left for this query")
        return self._queued_results.pop(0)

    def add(self, model: Any) -> None:
        self.added.append(model)

    def flush(self) -> None:
        self.flush_calls += 1

    def query(self, *_entities: Any) -> _FakeQuery:
        return _FakeQuery(self)


def _scalar(value: int) -> _FakeExecuteResult:
    return _FakeExecuteResult(scalar_value=value)


def _rows(value: list[Any]) -> _FakeExecuteResult:
    return _FakeExecuteResult(rows=value)


@dataclass(frozen=True)
class _SyncRow:
    id: str


@dataclass(frozen=True)
class _InstallRow:
    install_state: ConnectorInstallState


class TestFounderCommandDomainService:
    def test_specialty_ops_summary_counts_and_prioritization(self) -> None:
        # preplan, hazard, lz, duty, blocked, packet failure
        fake_db = _FakeDB([
            _scalar(3),
            _scalar(2),
            _scalar(1),
            _scalar(1),
            _scalar(4),
            _scalar(0),
        ])

        service = FounderCommandDomainService(cast(Any, fake_db))
        result = service.get_specialty_ops_summary()

        assert result.preplan_gaps == 3
        assert result.active_hazard_flags == 2
        assert result.pending_lz_confirmations == 1
        assert result.duty_time_warnings == 1
        assert result.specialty_missions_blocked == 4
        assert result.mission_packet_failures == 0

        actions = cast(list[FounderCommandAction], result.top_actions)
        assert len(actions) == 5
        assert actions[0].severity == "critical"
        assert "hazard" in actions[0].summary.lower()

    def test_records_command_summary_counts_and_prioritization(self) -> None:
        # draft/unsealed, signature gaps, low ocr, custody anomalies,
        # pending releases, failed exports, open qa
        fake_db = _FakeDB([
            _scalar(10),
            _scalar(7),
            _scalar(5),
            _scalar(2),
            _scalar(3),
            _scalar(4),
            _scalar(9),
        ])

        service = FounderCommandDomainService(cast(Any, fake_db))
        result = service.get_records_command_summary()

        assert result.draft_or_unsealed_records == 10
        assert result.signature_gaps == 7
        assert result.low_confidence_ocr_results == 5
        assert result.chain_of_custody_anomalies == 2
        assert result.pending_release_authorizations == 3
        assert result.failed_record_exports == 4
        assert result.open_qa_exceptions == 9

        actions = cast(list[FounderCommandAction], result.top_actions)
        assert len(actions) == 5
        assert actions[0].severity == "critical"
        assert "chain-of-custody" in actions[0].summary.lower()

    def test_integration_command_summary_counts_and_prioritization(self) -> None:
        # degraded install, failed sync, dead-letter, webhook retry,
        # key issues, quota denial windows
        fake_db = _FakeDB([
            _scalar(3),
            _scalar(6),
            _scalar(8),
            _scalar(4),
            _scalar(2),
            _scalar(5),
        ])

        service = FounderCommandDomainService(cast(Any, fake_db))
        result = service.get_integration_command_summary()

        assert result.degraded_or_disabled_installs == 3
        assert result.failed_sync_jobs_24h == 6
        assert result.dead_letter_records_24h == 8
        assert result.pending_webhook_retries == 4
        assert result.revoked_or_rotating_api_credentials == 2
        assert result.quota_denial_windows_24h == 5

        actions = cast(list[FounderCommandAction], result.top_actions)
        assert len(actions) == 5
        assert actions[0].severity == "critical"
        assert "degraded or disabled" in actions[0].summary.lower()

    def test_list_failed_sync_jobs_passthrough(self) -> None:
        rows = [_SyncRow(id="s1"), _SyncRow(id="s2")]
        fake_db = _FakeDB([_rows(rows)])

        service = FounderCommandDomainService(cast(Any, fake_db))
        result = service.list_failed_sync_jobs(limit=10)

        assert result == rows
        assert fake_db.execute_calls == 1

    def test_create_connector_sync_job_writes_job_and_audit(self) -> None:
        tenant_id = uuid.uuid4()
        actor_user_id = uuid.uuid4()
        install_id = uuid.uuid4()

        fake_db = _FakeDB([_FakeExecuteResult(scalar_value=_InstallRow(install_state=ConnectorInstallState.ACTIVE))])
        service = FounderCommandDomainService(cast(Any, fake_db))

        job = service.create_connector_sync_job(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            tenant_connector_install_id=install_id,
            direction="OUTBOUND",
            state="QUEUED",
            records_attempted=0,
            records_succeeded=0,
            records_failed=0,
            error_summary={"x12_payload_base64": "dGVzdA=="},
        )

        assert str(job.state) == "QUEUED"
        assert job.records_attempted == 0
        assert job.records_failed == 0
        assert job.started_at is None
        assert fake_db.flush_calls == 2
        assert len(fake_db.added) == 2

    def test_create_connector_sync_job_invalid_state_raises(self) -> None:
        fake_db = _FakeDB([_FakeExecuteResult(scalar_value=_InstallRow(install_state=ConnectorInstallState.ACTIVE))])
        service = FounderCommandDomainService(cast(Any, fake_db))

        try:
            service.create_connector_sync_job(
                tenant_id=uuid.uuid4(),
                actor_user_id=uuid.uuid4(),
                tenant_connector_install_id=uuid.uuid4(),
                direction="OUTBOUND",
                state="NOT_A_REAL_STATE",
                records_attempted=0,
                records_succeeded=0,
                records_failed=0,
                error_summary={},
            )
            raise AssertionError("Expected AppError for invalid state")
        except AppError as exc:
            assert exc.code == "VALIDATION_ERROR"

    def test_create_connector_sync_job_rejects_non_queued_state(self) -> None:
        fake_db = _FakeDB([_FakeExecuteResult(scalar_value=_InstallRow(install_state=ConnectorInstallState.ACTIVE))])
        service = FounderCommandDomainService(cast(Any, fake_db))

        try:
            service.create_connector_sync_job(
                tenant_id=uuid.uuid4(),
                actor_user_id=uuid.uuid4(),
                tenant_connector_install_id=uuid.uuid4(),
                direction="OUTBOUND",
                state="FAILED",
                records_attempted=0,
                records_succeeded=0,
                records_failed=0,
                error_summary={},
            )
            raise AssertionError("Expected AppError for non-queued state")
        except AppError as exc:
            assert exc.code == "VALIDATION_ERROR"

    def test_create_connector_sync_job_rejects_non_zero_counters(self) -> None:
        fake_db = _FakeDB([_FakeExecuteResult(scalar_value=_InstallRow(install_state=ConnectorInstallState.ACTIVE))])
        service = FounderCommandDomainService(cast(Any, fake_db))

        try:
            service.create_connector_sync_job(
                tenant_id=uuid.uuid4(),
                actor_user_id=uuid.uuid4(),
                tenant_connector_install_id=uuid.uuid4(),
                direction="OUTBOUND",
                state="QUEUED",
                records_attempted=1,
                records_succeeded=0,
                records_failed=0,
                error_summary={},
            )
            raise AssertionError("Expected AppError for non-zero counters")
        except AppError as exc:
            assert exc.code == "VALIDATION_ERROR"

    def test_add_sync_dead_letter_writes_record_and_audit(self) -> None:
        tenant_id = uuid.uuid4()
        actor_user_id = uuid.uuid4()
        sync_job_id = uuid.uuid4()

        fake_db = _FakeDB([_FakeExecuteResult(scalar_value=object())])
        service = FounderCommandDomainService(cast(Any, fake_db))

        letter = service.add_sync_dead_letter(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            connector_sync_job_id=sync_job_id,
            external_record_ref="ext-123",
            reason="payload mismatch",
            payload={"field": "value"},
        )

        assert letter.external_record_ref == "ext-123"
        assert letter.reason == "payload mismatch"
        assert fake_db.flush_calls == 2
        assert len(fake_db.added) == 2
