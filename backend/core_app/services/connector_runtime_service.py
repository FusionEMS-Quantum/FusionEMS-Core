"""Runtime orchestration for connector sync jobs.

This service executes queued connector sync jobs using provider-specific executors,
updates job state deterministically, records dead-letter payloads on failures,
and writes integration audit events for every execution stage.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.core.config import Settings, get_settings
from core_app.integrations.graph_service import GraphApiError, GraphNotConfigured, get_graph_client
from core_app.integrations.officeally import (
    OfficeAllyClientError,
    OfficeAllySftpConfig,
    submit_837_via_sftp,
)
from core_app.models.integration_connectors import (
    ConnectorCatalog,
    ConnectorProfile,
    ConnectorSyncJob,
    IntegrationAuditEvent,
    SyncDeadLetter,
    SyncJobState,
    TenantConnectorInstall,
)


@dataclass(frozen=True)
class DeadLetterRecord:
    """A sync payload that should be persisted to dead-letter storage."""

    external_record_ref: str
    reason: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectorExecutionResult:
    """Normalized execution result returned by connector executors."""

    success: bool
    records_attempted: int
    records_succeeded: int
    records_failed: int
    error_summary: dict[str, object] = field(default_factory=dict)
    dead_letters: list[DeadLetterRecord] = field(default_factory=list)

    @classmethod
    def ok(
        cls,
        *,
        records_attempted: int,
        records_succeeded: int,
        error_summary: dict[str, object] | None = None,
    ) -> ConnectorExecutionResult:
        return cls(
            success=True,
            records_attempted=records_attempted,
            records_succeeded=records_succeeded,
            records_failed=max(0, records_attempted - records_succeeded),
            error_summary=error_summary or {},
            dead_letters=[],
        )

    @classmethod
    def failed(
        cls,
        *,
        reason: str,
        external_record_ref: str,
        payload: dict[str, object] | None = None,
    ) -> ConnectorExecutionResult:
        return cls(
            success=False,
            records_attempted=1,
            records_succeeded=0,
            records_failed=1,
            error_summary={"reason": reason},
            dead_letters=[
                DeadLetterRecord(
                    external_record_ref=external_record_ref,
                    reason=reason,
                    payload=payload or {},
                )
            ],
        )


class ConnectorExecutor(Protocol):
    """Provider-specific connector execution protocol."""

    def execute(
        self,
        *,
        catalog: ConnectorCatalog,
        profile: ConnectorProfile,
        install: TenantConnectorInstall,
        job: ConnectorSyncJob,
    ) -> ConnectorExecutionResult:
        ...


class OfficeAllySftpExecutor:
    """Executes Office Ally 837 submission jobs over SFTP."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def execute(
        self,
        *,
        catalog: ConnectorCatalog,
        profile: ConnectorProfile,
        install: TenantConnectorInstall,
        job: ConnectorSyncJob,
    ) -> ConnectorExecutionResult:
        del catalog, install

        error_payload = job.error_summary if isinstance(job.error_summary, dict) else {}
        x12_payload_b64 = error_payload.get("x12_payload_base64")
        if not isinstance(x12_payload_b64, str) or not x12_payload_b64.strip():
            return ConnectorExecutionResult.failed(
                reason="Missing x12_payload_base64 in sync job payload",
                external_record_ref=str(job.id),
                payload={"sync_job_id": str(job.id)},
            )

        try:
            x12_bytes = base64.b64decode(x12_payload_b64, validate=True)
        except (binascii.Error, ValueError):
            return ConnectorExecutionResult.failed(
                reason="Invalid base64 payload for x12_payload_base64",
                external_record_ref=str(job.id),
                payload={"sync_job_id": str(job.id)},
            )

        file_name = str(error_payload.get("file_name") or f"sync-{job.id}.x12")
        cfg = OfficeAllySftpConfig(
            host=self._settings.officeally_sftp_host,
            port=self._settings.officeally_sftp_port,
            username=self._settings.officeally_sftp_username,
            password=self._settings.officeally_sftp_password,
            remote_dir=str(
                profile.config_payload.get("remote_dir")
                or self._settings.officeally_sftp_remote_dir
                or "/"
            ),
        )

        try:
            remote_path = submit_837_via_sftp(cfg=cfg, file_name=file_name, x12_bytes=x12_bytes)
            return ConnectorExecutionResult.ok(
                records_attempted=1,
                records_succeeded=1,
                error_summary={"remote_path": remote_path},
            )
        except (OfficeAllyClientError, OSError, RuntimeError) as exc:
            return ConnectorExecutionResult.failed(
                reason=f"OfficeAlly sync failed: {exc}",
                external_record_ref=file_name,
                payload={"sync_job_id": str(job.id), "file_name": file_name},
            )


class GraphMailboxPullExecutor:
    """Executes Microsoft Graph mailbox polling jobs."""

    def execute(
        self,
        *,
        catalog: ConnectorCatalog,
        profile: ConnectorProfile,
        install: TenantConnectorInstall,
        job: ConnectorSyncJob,
    ) -> ConnectorExecutionResult:
        del catalog, install

        top_raw = profile.config_payload.get("top", 25)
        folder = str(profile.config_payload.get("folder") or "inbox")
        if isinstance(top_raw, bool):
            top = 25
        elif isinstance(top_raw, int):
            top = max(1, min(250, top_raw))
        elif isinstance(top_raw, str):
            try:
                top = max(1, min(250, int(top_raw)))
            except ValueError:
                top = 25
        else:
            top = 25

        try:
            client = get_graph_client()
            payload = client.list_messages(top=top, folder=folder)
            messages = payload.get("value", [])
            count = len(messages) if isinstance(messages, list) else 0
            return ConnectorExecutionResult.ok(
                records_attempted=count,
                records_succeeded=count,
                error_summary={"folder": folder, "fetched": count},
            )
        except (GraphNotConfigured, GraphApiError, RuntimeError, ValueError) as exc:
            return ConnectorExecutionResult.failed(
                reason=f"Graph mailbox pull failed: {exc}",
                external_record_ref=str(job.id),
                payload={"sync_job_id": str(job.id), "folder": folder},
            )


class ConnectorRuntimeService:
    """Coordinates provider-specific connector execution and auditing."""

    def __init__(self, db: Session, *, settings: Settings | None = None) -> None:
        self.db = db
        self._settings = settings or get_settings()
        self._executors: dict[str, ConnectorExecutor] = {
            "OFFICEALLY": OfficeAllySftpExecutor(self._settings),
            "OFFICEALLYSFTP": OfficeAllySftpExecutor(self._settings),
            "OFFICE_ALLY": OfficeAllySftpExecutor(self._settings),
            "MICROSOFTGRAPH": GraphMailboxPullExecutor(),
            "GRAPHMAIL": GraphMailboxPullExecutor(),
        }

    @staticmethod
    def _normalize_connector_key(connector_key: str) -> str:
        return "".join(ch for ch in connector_key.upper() if ch.isalnum() or ch == "_")

    def process_queued_jobs(
        self,
        *,
        limit: int = 10,
        actor_user_id: uuid.UUID | None = None,
    ) -> int:
        """Process up to `limit` queued sync jobs in FIFO order."""

        processed = 0
        for _ in range(max(1, limit)):
            queued_job = self.db.execute(
                select(ConnectorSyncJob)
                .where(ConnectorSyncJob.state == SyncJobState.QUEUED)
                .order_by(ConnectorSyncJob.created_at.asc())
                .limit(1)
            ).scalar_one_or_none()
            if queued_job is None:
                break

            self.execute_sync_job(sync_job_id=queued_job.id, actor_user_id=actor_user_id)
            self.db.commit()
            processed += 1

        return processed

    def execute_sync_job(
        self,
        *,
        sync_job_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> ConnectorSyncJob:
        """Execute a single sync job and persist state/audit updates."""

        job = self.db.execute(
            select(ConnectorSyncJob).where(ConnectorSyncJob.id == sync_job_id)
        ).scalar_one_or_none()
        if job is None:
            raise RuntimeError(f"Sync job not found: {sync_job_id}")

        install = self.db.execute(
            select(TenantConnectorInstall).where(
                TenantConnectorInstall.id == job.tenant_connector_install_id,
                TenantConnectorInstall.tenant_id == job.tenant_id,
            )
        ).scalar_one_or_none()
        if install is None:
            raise RuntimeError("Connector install not found for sync job tenant")

        profile = self.db.execute(
            select(ConnectorProfile).where(
                ConnectorProfile.id == install.connector_profile_id,
                ConnectorProfile.tenant_id == job.tenant_id,
            )
        ).scalar_one_or_none()
        if profile is None:
            raise RuntimeError("Connector profile not found for sync job tenant")

        catalog = self.db.execute(
            select(ConnectorCatalog).where(ConnectorCatalog.id == profile.connector_catalog_id)
        ).scalar_one_or_none()
        if catalog is None:
            raise RuntimeError("Connector catalog entry missing for sync job")

        now = datetime.now(UTC)
        if job.state == SyncJobState.QUEUED:
            job.state = SyncJobState.RUNNING
        if job.started_at is None:
            job.started_at = now

        self.db.add(
            IntegrationAuditEvent(
                tenant_id=job.tenant_id,
                entity_type="ConnectorSyncJob",
                entity_id=job.id,
                event_type="SYNC_JOB_EXECUTION_STARTED",
                actor_user_id=actor_user_id,
                event_payload={"connector_key": catalog.connector_key},
            )
        )
        self.db.flush()

        executor = self._executors.get(self._normalize_connector_key(catalog.connector_key))
        if executor is None:
            result = ConnectorExecutionResult.failed(
                reason=f"No executor registered for connector: {catalog.connector_key}",
                external_record_ref=str(job.id),
                payload={"connector_key": catalog.connector_key},
            )
        else:
            result = executor.execute(
                catalog=catalog,
                profile=profile,
                install=install,
                job=job,
            )

        job.records_attempted = result.records_attempted
        job.records_succeeded = result.records_succeeded
        job.records_failed = result.records_failed
        job.error_summary = result.error_summary
        job.completed_at = datetime.now(UTC)
        job.state = SyncJobState.COMPLETED if result.success else SyncJobState.FAILED

        for dead_letter in result.dead_letters:
            self.db.add(
                SyncDeadLetter(
                    tenant_id=job.tenant_id,
                    connector_sync_job_id=job.id,
                    external_record_ref=dead_letter.external_record_ref,
                    reason=dead_letter.reason,
                    payload=dead_letter.payload,
                )
            )

        self.db.add(
            IntegrationAuditEvent(
                tenant_id=job.tenant_id,
                entity_type="ConnectorSyncJob",
                entity_id=job.id,
                event_type=(
                    "SYNC_JOB_EXECUTION_COMPLETED"
                    if result.success
                    else "SYNC_JOB_EXECUTION_FAILED"
                ),
                actor_user_id=actor_user_id,
                event_payload={
                    "records_attempted": result.records_attempted,
                    "records_succeeded": result.records_succeeded,
                    "records_failed": result.records_failed,
                    "error_summary": result.error_summary,
                },
            )
        )
        self.db.flush()

        return job
